import json
from datetime import datetime

from fastapi import FastAPI, Request

from compliance import check_compliance
from data import load_accounts
from tools import TOOL_HANDLERS

app = FastAPI(title="Collections Voice Agent Backend")


@app.post("/vapi/webhook")
async def vapi_webhook(request: Request):
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

    return {"ok": True}


@app.post("/call/check")
async def call_check(request: Request):
    body = await request.json()
    account_number = body.get("account_number", "")
    return check_compliance(account_number)


@app.get("/accounts")
async def get_accounts():
    return load_accounts()


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
