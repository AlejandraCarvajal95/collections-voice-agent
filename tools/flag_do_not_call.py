from datetime import date

from data import load_accounts, save_accounts, find_account


def handle_flag_do_not_call(arguments: dict) -> dict:
    """Set do_not_call = True on the account (FDCPA §1692c(c) cease-communication request)."""
    account_number = arguments.get("account_number", "")

    accounts = load_accounts()
    account = find_account(accounts, account_number)

    if not account:
        return {"status": "error", "message": "Account not found"}

    account["do_not_call"] = True
    account["last_contact_date"] = date.today().isoformat()

    save_accounts(accounts)

    return {
        "status": "success",
        "message": "Do not call flag has been set. No further calls will be made to this consumer.",
    }
