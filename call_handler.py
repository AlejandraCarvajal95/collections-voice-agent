import json
from datetime import date, datetime
from pathlib import Path

from data import load_accounts, save_accounts, find_account

CALL_LOGS_FILE = Path(__file__).parent / "call_logs.json"


def handle_end_of_call(message: dict) -> dict:
    call = message.get("call", {})
    call_id = call.get("id", "unknown")
    started_at = call.get("startedAt", "")
    ended_at = call.get("endedAt", "")
    ended_reason = message.get("endedReason", "unknown")
    transcript = message.get("transcript", "")
    summary = message.get("summary", "")

    overrides = call.get("assistantOverrides", {})
    variables = overrides.get("variableValues", {})
    account_number = variables.get("account_number", "")

    if account_number:
        accounts = load_accounts()
        account = find_account(accounts, account_number)
        if account:
            account["last_contact_date"] = date.today().isoformat()
            save_accounts(accounts)

    duration = None
    if started_at and ended_at:
        try:
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
            duration = int((end - start).total_seconds())
        except ValueError:
            pass

    log_entry = {
        "call_id": call_id,
        "account_number": account_number,
        "timestamp": datetime.now().isoformat(),
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": duration,
        "ended_reason": ended_reason,
        "summary": summary,
        "transcript": transcript,
    }

    logs = json.loads(CALL_LOGS_FILE.read_text()) if CALL_LOGS_FILE.exists() else []
    logs.append(log_entry)
    CALL_LOGS_FILE.write_text(json.dumps(logs, indent=2))

    return {"ok": True}


def get_call_logs() -> list[dict]:
    logs = json.loads(CALL_LOGS_FILE.read_text()) if CALL_LOGS_FILE.exists() else []
    return logs
