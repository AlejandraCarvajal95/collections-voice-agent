from datetime import date

from data import load_accounts, save_accounts, find_account


def handle_flag_attorney(arguments: dict) -> dict:
    """Set has_attorney = True on the account (FDCPA §1692c(a)(2) — all contact must go through counsel)."""
    account_number = arguments.get("account_number", "")

    accounts = load_accounts()
    account = find_account(accounts, account_number)

    if not account:
        return {"status": "error", "message": "Account not found"}

    account["has_attorney"] = True
    account["last_contact_date"] = date.today().isoformat()

    save_accounts(accounts)

    return {
        "status": "success",
        "message": "Attorney representation noted. All future communication will be directed to their attorney.",
    }
