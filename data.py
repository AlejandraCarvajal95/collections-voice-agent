import json
import copy
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


def reset_data():
    """Restore accounts to the startup snapshot and clear all call logs."""
    global _original_accounts
    if _original_accounts is None:
        return
    save_accounts(copy.deepcopy(_original_accounts))
    with open(CALL_LOGS_FILE, "w") as f:
        json.dump([], f)
