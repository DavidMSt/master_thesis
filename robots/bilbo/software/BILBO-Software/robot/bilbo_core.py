from core.utils.callbacks import callback_definition
from core.utils.events import event_definition





def error_handler(severity, message):
    print(
        f"[{severity}] {message}"
    )

@event_definition
class BILBO_Core_Events:
    ...


@callback_definition
class BILBO_Core_Callbacks:
    ...


class BILBO_Core:

    def __init__(self):
        ...
