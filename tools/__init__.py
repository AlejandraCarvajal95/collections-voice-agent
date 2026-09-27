from tools.record_payment import handle_record_payment
from tools.set_promise_to_pay import handle_set_promise_to_pay
from tools.flag_do_not_call import handle_flag_do_not_call

TOOL_HANDLERS = {
    "record_payment": handle_record_payment,
    "set_promise_to_pay": handle_set_promise_to_pay,
    "flag_do_not_call": handle_flag_do_not_call,
}
