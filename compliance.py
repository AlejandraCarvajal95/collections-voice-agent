from datetime import datetime
from zoneinfo import ZoneInfo

from data import load_accounts, find_account, save_accounts

STATE_TIMEZONES = {
    "AL": "America/Chicago",
    "AK": "America/Anchorage",
    "AZ": "America/Phoenix",
    "AR": "America/Chicago",
    "CA": "America/Los_Angeles",
    "CO": "America/Denver",
    "CT": "America/New_York",
    "DE": "America/New_York",
    "FL": "America/New_York",
    "GA": "America/New_York",
    "HI": "Pacific/Honolulu",
    "ID": "America/Boise",
    "IL": "America/Chicago",
    "IN": "America/Indiana/Indianapolis",
    "IA": "America/Chicago",
    "KS": "America/Chicago",
    "KY": "America/New_York",
    "LA": "America/Chicago",
    "ME": "America/New_York",
    "MD": "America/New_York",
    "MA": "America/New_York",
    "MI": "America/Detroit",
    "MN": "America/Chicago",
    "MS": "America/Chicago",
    "MO": "America/Chicago",
    "MT": "America/Denver",
    "NE": "America/Chicago",
    "NV": "America/Los_Angeles",
    "NH": "America/New_York",
    "NJ": "America/New_York",
    "NM": "America/Denver",
    "NY": "America/New_York",
    "NC": "America/New_York",
    "ND": "America/Chicago",
    "OH": "America/New_York",
    "OK": "America/Chicago",
    "OR": "America/Los_Angeles",
    "PA": "America/New_York",
    "RI": "America/New_York",
    "SC": "America/New_York",
    "SD": "America/Chicago",
    "TN": "America/Chicago",
    "TX": "America/Chicago",
    "UT": "America/Denver",
    "VT": "America/New_York",
    "VA": "America/New_York",
    "WA": "America/Los_Angeles",
    "WV": "America/New_York",
    "WI": "America/Chicago",
    "WY": "America/Denver",
    "DC": "America/New_York",
}

CALL_ATTEMPTS_LIMIT = 7


def check_compliance(account_number: str) -> dict:
    accounts = load_accounts()
    account = find_account(accounts, account_number)

    if not account:
        return {"allowed": False, "reason": "Account not found"}

    # Check 1: Cease and desist
    if account.get("cease_and_desist"):
        return {
            "allowed": False,
            "reason": "Consumer has an active cease-and-desist request. No further contact permitted.",
        }

    # Check 2: Do not call
    if account.get("do_not_call"):
        return {
            "allowed": False,
            "reason": "Consumer has requested no further calls.",
        }

    # Check 3: Attorney representation
    if account.get("has_attorney"):
        return {
            "allowed": False,
            "reason": "Consumer is represented by an attorney. Contact must go through their counsel.",
        }

    # Check 4: Reg F — 7 calls per 7 days
    if account.get("call_attempts_last_7_days", 0) >= CALL_ATTEMPTS_LIMIT:
        return {
            "allowed": False,
            "reason": f"Call frequency limit reached ({CALL_ATTEMPTS_LIMIT} attempts in the last 7 days). Reg F §1006.14(b)(2).",
        }

    # Check 5: FDCPA calling hours — 8am to 9pm in consumer's local time
    state = account.get("consumer_state", "")
    tz_name = STATE_TIMEZONES.get(state)
    if tz_name:
        local_time = datetime.now(ZoneInfo(tz_name))
        hour = local_time.hour
        if hour < 8 or hour >= 21:
            return {
                "allowed": False,
                "reason": f"Outside calling hours in {state} (currently {local_time.strftime('%I:%M %p')} local). FDCPA §1692c(a)(1) allows calls only between 8:00 AM and 9:00 PM.",
            }

    # All checks passed — increment call counter
    account["call_attempts_last_7_days"] = account.get("call_attempts_last_7_days", 0) + 1
    save_accounts(accounts)

    return {
        "allowed": True,
        "account_number": account_number,
        "consumer_name": f"{account['consumer_first_name']} {account['consumer_last_name']}",
        "call_attempt_number": account["call_attempts_last_7_days"],
    }
