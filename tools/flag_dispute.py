from datetime import date

from data import load_accounts, save_accounts, find_account


def handle_flag_dispute(arguments: dict) -> dict:
    """Set active_dispute = True on the account (FDCPA §1692g debt validation request)."""
    account_number = arguments.get("account_number", "")

    accounts = load_accounts()
    account = find_account(accounts, account_number)

    if not account:
        return {"status": "error", "message": "Account not found"}

    account["active_dispute"] = True
    account["last_contact_date"] = date.today().isoformat()

    save_accounts(accounts)

    return {
        "status": "success",
        "message": "Dispute noted, validation letter will be sent within 30 days.",
    }
