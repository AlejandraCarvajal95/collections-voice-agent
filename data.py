import json
import copy
import random
from pathlib import Path

ACCOUNTS_FILE = Path(__file__).parent / "data" / "accounts.json"
CALL_LOGS_FILE = Path(__file__).parent / "data" / "call_logs.json"

_original_accounts: list[dict] | None = None


def load_accounts() -> list[dict]:
    with open(ACCOUNTS_FILE) as f:
        return json.load(f)


def save_accounts(accounts: list[dict]) -> None:
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=2)


def find_account(accounts: list[dict], account_number: str) -> dict | None:
    """Return the account matching account_number, or None if not found."""
    for account in accounts:
        if account["account_number"] == account_number:
            return account
    return None


def snapshot_original():
    """Save the initial state of accounts on startup so reset_data() can restore it."""
    global _original_accounts
    if _original_accounts is None:
        _original_accounts = copy.deepcopy(load_accounts())


def add_account(fields: dict) -> dict:
    """Append a new custom account to accounts.json and return it."""
    accounts = load_accounts()
    number = "CH" + str(random.randint(1000000, 9999999))
    account = {
        "account_number": number,
        "consumer_first_name": fields["consumer_first_name"],
        "consumer_last_name": fields["consumer_last_name"],
        "consumer_dob": fields.get("consumer_dob", "1990-01-01"),
        "consumer_state": fields["consumer_state"],
        "phone": "+15550000000",
        "product_type": "Credit Card",
        "last_4_digits": number[-4:],
        "total_balance": fields.get("total_balance", 0.0),
        "past_due_amount": fields.get("past_due_amount", 0.0),
        "minimum_payment": fields.get("minimum_payment", 0.0),
        "days_past_due": fields.get("days_past_due", 30),
        "missed_payments": fields.get("missed_payments", 1),
        "cease_and_desist": fields.get("cease_and_desist", False),
        "do_not_call": fields.get("do_not_call", False),
        "has_attorney": fields.get("has_attorney", False),
        "active_dispute": fields.get("active_dispute", False),
        "promise_to_pay_exists": False,
        "promise_to_pay_date": None,
        "promise_to_pay_amount": None,
        "last_contact_date": None,
        "call_attempts_last_7_days": fields.get("call_attempts_last_7_days", 0),
        "callback_number": "+18005550000",
        "department": "Credit Card Services",
    }
    accounts.append(account)
    save_accounts(accounts)
    return account


def reset_data():
    """Restore accounts to the startup snapshot and clear all call logs."""
    global _original_accounts
    if _original_accounts is None:
        return
    save_accounts(copy.deepcopy(_original_accounts))
    with open(CALL_LOGS_FILE, "w") as f:
        json.dump([], f)
