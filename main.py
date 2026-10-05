import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from call_handler import handle_end_of_call, get_call_logs
from compliance import check_compliance, increment_call_attempt
from data import load_accounts, add_account, snapshot_original, reset_data
from tools import TOOL_HANDLERS


class CallCheckRequest(BaseModel):
    account_number: str


class NewAccountRequest(BaseModel):
    consumer_first_name: str
    consumer_last_name: str
    consumer_state: str
    consumer_dob: str = "1990-01-01"
    total_balance: float = 0.0
    past_due_amount: float = 0.0
    minimum_payment: float = 0.0
    days_past_due: int = 30
    missed_payments: int = 1
    call_attempts_last_7_days: int = 0
    cease_and_desist: bool = False
    do_not_call: bool = False
    has_attorney: bool = False
    active_dispute: bool = False

app = FastAPI(title="Collections Voice Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DASHBOARD_DIR = Path(__file__).parent / "dashboard"


@app.on_event("startup")
def on_startup():
    snapshot_original()


@app.post("/vapi/webhook")
async def vapi_webhook(request: Request):
    # Routes tool-calls by function name via TOOL_HANDLERS; also handles end-of-call-report.
    payload = await request.json()
    message = payload.get("message", {})
    message_type = message.get("type", "")

    if message_type == "tool-calls":
        tool_calls = message.get("toolCallList", [])
        results = []

        for tool_call in tool_calls:
            tool_call_id = tool_call.get("id", "")
            function = tool_call.get("function", {})
            function_name = function.get("name", "")
            arguments = function.get("arguments", {})

            handler = TOOL_HANDLERS.get(function_name)
            if handler:
                result = handler(arguments)
            else:
                result = {"error": f"Unknown tool: {function_name}"}

            results.append({
                "toolCallId": tool_call_id,
                "result": json.dumps(result),
            })

        return {"results": results}

    if message_type == "end-of-call-report":
        return handle_end_of_call(message)

    return {"ok": True}


@app.post("/call/check")
async def call_check(body: CallCheckRequest):
    return check_compliance(body.account_number)


@app.post("/call/start")
async def call_start(body: CallCheckRequest):
    return increment_call_attempt(body.account_number)


@app.get("/accounts")
async def get_accounts():
    return load_accounts()


@app.post("/accounts")
async def create_account(body: NewAccountRequest):
    return add_account(body.model_dump())


@app.get("/call/logs")
async def call_logs():
    return get_call_logs()


@app.get("/config")
async def get_config(x_dashboard_token: str = Header(default="")):
    # Returns Vapi keys to the dashboard. Requires a static token header to prevent public exposure.
    expected = os.environ.get("DASHBOARD_TOKEN", "")
    if not expected or x_dashboard_token != expected:
        raise HTTPException(status_code=403, detail="Forbidden")
    return {
        "vapi_public_key": os.environ.get("VAPI_PUBLIC_KEY", ""),
        "vapi_assistant_id": os.environ.get("VAPI_ASSISTANT_ID", ""),
        "transfer_number": os.environ.get("TRANSFER_NUMBER", ""),
    }


@app.post("/data/reset")
async def data_reset():
    reset_data()
    return {"status": "reset", "timestamp": datetime.now().isoformat()}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/dashboard")
async def dashboard():
    return FileResponse(DASHBOARD_DIR / "index.html")


app.mount("/dashboard/static", StaticFiles(directory=DASHBOARD_DIR), name="dashboard-static")
