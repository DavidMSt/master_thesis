from core.communication.wifi.tcp.protocols.tcp_json_protocol import TCP_JSON_Message
from core.device import Device
from robots.bilbo.robot.bilbo_definitions import BILBO_Control_Mode
from core.utils.callbacks import callback_definition, CallbackContainer
from core.utils.events import event_definition, ConditionEvent
from core.utils.logging_utils import Logger, LOG_LEVELS
from core.utils.sound.sound import speak


@callback_definition
class BILBO_Core_Callbacks:
    stream: CallbackContainer


# ======================================================================================================================
@event_definition
class BILBO_Core_Events:
    control_mode_changed: ConditionEvent = ConditionEvent(flags=[('mode', BILBO_Control_Mode)])
    control_configuration_changed: ConditionEvent
    control_error: ConditionEvent
    stream: ConditionEvent


@event_definition
class BILBO_Interface_Events:
    resume: ConditionEvent
    revert: ConditionEvent


class BILBO_Core:

    # ==================================================================================================================
    def __init__(self, robot_id: str, device: Device):
        self.device = device
        self.id = robot_id
        self.logger = Logger(f"{self.id}")
        self.logger.setLevel('DEBUG')

        self.events = BILBO_Core_Events()
        self.interface_events = BILBO_Interface_Events()

        self.device.events.event.on(self._handleLogMessage, flags={'event': 'log'}, input_resource=True)
        self.device.events.event.on(self._handleSpeakEventMessage, flags={'event': 'speak'}, input_resource=True)
        self.device.events.stream.on(self._handleStream, input_resource=True)

    # ------------------------------------------------------------------------------------------------------------------
    def beep(self, frequency=1000, time_ms=250, repeats=1):
        self.device.function(function='beep', data={'frequency': frequency, 'time_ms': time_ms, 'repeats': repeats})

    # ------------------------------------------------------------------------------------------------------------------
    def speak(self, text):
        self.device.function(function='speak', data={'message': text})

    # ------------------------------------------------------------------------------------------------------------------
    def _handleLogMessage(self, log_message: TCP_JSON_Message):
        log_data = log_message.data

        if log_data['level'] == LOG_LEVELS['ERROR']:
            self.logger.error(f"({log_data['logger']}): {log_data['message']}")
        elif log_data['level'] == LOG_LEVELS['WARNING']:
            self.logger.warning(f"({log_data['logger']}): {log_data['message']}")
        elif log_data['level'] == LOG_LEVELS['INFO']:
            self.logger.info(f"({log_data['logger']}): {log_data['message']}")
        elif log_data['level'] == LOG_LEVELS['DEBUG']:
            self.logger.debug(f"({log_data['logger']}): {log_data['message']}")

        if log_data.get('speak', False):
            speak(f"{self.id}: {log_data['message']}")

    # ------------------------------------------------------------------------------------------------------------------
    def _handleSpeakEventMessage(self, message: TCP_JSON_Message):
        data = message.data
        if data.get('message', None) is not None:
            speak(f"{self.id}: {data['message']}")

    # ------------------------------------------------------------------------------------------------------------------
    def _handleStream(self, data):
        self.events.stream.set(data)
