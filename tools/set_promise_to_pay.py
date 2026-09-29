from datetime import date

from data import load_accounts, save_accounts, find_account


def handle_set_promise_to_pay(arguments: dict) -> dict:
    """Log a promise-to-pay commitment. Validates that the promised date is in the future."""
    account_number = arguments.get("account_number", "")
    amount = arguments.get("amount", 0)
    pay_date = arguments.get("date", "")

    accounts = load_accounts()
    account = find_account(accounts, account_number)

    if not account:
        return {"status": "error", "message": "Account not found"}

    try:
        promised = date.fromisoformat(pay_date)
        if promised <= date.today():
            return {"status": "error", "message": "The payment date must be a future date."}
    except ValueError:
        return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}

    today = date.today().strftime("%Y%m%d")
    confirmation = f"PTP-{today}-{account_number[-4:]}"

    account["promise_to_pay_exists"] = True
    account["promise_to_pay_date"] = pay_date
    account["promise_to_pay_amount"] = amount
    account["last_contact_date"] = date.today().isoformat()

    save_accounts(accounts)

    return {
        "status": "success",
        "confirmation_number": confirmation,
        "promise_amount": amount,
        "promise_date": pay_date,
    }
