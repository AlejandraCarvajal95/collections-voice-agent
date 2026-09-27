from tools.record_payment import handle_record_payment
from tools.set_promise_to_pay import handle_set_promise_to_pay
from tools.flag_do_not_call import handle_flag_do_not_call
from tools.flag_dispute import handle_flag_dispute
from tools.flag_attorney import handle_flag_attorney

TOOL_HANDLERS = {
    "record_payment": handle_record_payment,
    "set_promise_to_pay": handle_set_promise_to_pay,
    "flag_do_not_call": handle_flag_do_not_call,
    "flag_dispute": handle_flag_dispute,
    "flag_attorney": handle_flag_attorney,
}
