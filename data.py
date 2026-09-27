import json
from pathlib import Path

ACCOUNTS_FILE = Path(__file__).parent / "accounts.json"


def load_accounts() -> list[dict]:
    with open(ACCOUNTS_FILE) as f:
        return json.load(f)


def save_accounts(accounts: list[dict]) -> None:
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=2)


def find_account(accounts: list[dict], account_number: str) -> dict | None:
    for account in accounts:
        if account["account_number"] == account_number:
            return account
    return None
