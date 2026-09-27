from datetime import date

from data import load_accounts, save_accounts, find_account


def handle_record_payment(arguments: dict) -> dict:
    account_number = arguments.get("account_number", "")
    amount = arguments.get("amount", 0)
    method = arguments.get("method", "phone")

    accounts = load_accounts()
    account = find_account(accounts, account_number)

    if not account:
        return {"status": "error", "message": "Account not found"}

    today = date.today().strftime("%Y%m%d")
    confirmation = f"PAY-{today}-{account_number[-4:]}"

    account["past_due_amount"] = round(account["past_due_amount"] - amount, 2)
    if account["past_due_amount"] < 0:
        account["past_due_amount"] = 0
    account["last_contact_date"] = date.today().isoformat()

    save_accounts(accounts)

    return {
        "status": "success",
        "confirmation_number": confirmation,
        "amount_paid": amount,
        "method": method,
        "remaining_past_due": account["past_due_amount"],
    }
