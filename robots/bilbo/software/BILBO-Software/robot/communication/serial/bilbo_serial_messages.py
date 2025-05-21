import ctypes
import enum

from core.communication.serial.serial_interface import SerialMessage, SerialCommandType
from robot.lowlevel.stm32_control import bilbo_control_configuration_ll_t
from robot.lowlevel.stm32_messages import *
from core.utils.logging_utils import Logger


# ======================================================================================================================
class bilbo_debug_message_data_type(ctypes.Structure):
    _fields_ = [
        ("flag", ctypes.c_uint8),
        ("text", ctypes.c_char * 100)
    ]


def debugprint(data: bilbo_debug_message_data_type, *args, **kwargs):
    logger = Logger("BILBO DEBUG", "DEBUG")
    try:
        flag = data['flag']
        text = data['text'].decode("utf-8")
        if flag == 0:
            logger.debug(f"DEBUG: {text}")
        if flag == 1:
            logger.info(f"{text}")
        if flag == 2:
            logger.warning(f"{text}")
        if flag == 3:
            logger.error(f"{text}")
    except Exception as e:
        ...


class BILBO_Debug_Message(SerialMessage):
    module: int = 1
    address: int = BILBO_LL_MESSAGE_PRINT
    command: SerialCommandType = SerialCommandType.UART_CMD_EVENT
    data_type: type = bilbo_debug_message_data_type
    callback = staticmethod(debugprint)


# ======================================================================================================================
class sequencer_event_t(enum.IntEnum):
    STARTED = 1
    FINISHED = 2
    ABORTED = 3


class sequencer_event_message_data_t(ctypes.Structure):
    _fields_ = [
        ("event", ctypes.c_uint8),
        ("sequence_id", ctypes.c_uint16),
        ("sequence_tick", ctypes.c_uint32),
        ("tick", ctypes.c_uint32)
    ]


class BILBO_Sequencer_Event_Message(SerialMessage):
    module: int = 1
    address: int = BILBO_LL_MESSAGE_SEQUENCER_EVENT
    command: SerialCommandType = SerialCommandType.UART_CMD_EVENT
    data_type: type = sequencer_event_message_data_t


# ======================================================================================================================
class bilbo_error_message_data_type(ctypes.Structure):
    _fields_ = [
        ('type', ctypes.c_uint8),
        ('error', ctypes.c_uint8),
        ('overall_error', ctypes.c_uint8)
    ]


class BILBO_Error_Message(SerialMessage):
    module = 1
    address = BILBO_LL_MESSAGE_ERROR
    command = SerialCommandType.UART_CMD_EVENT
    data_type = bilbo_error_message_data_type

# ======================================================================================================================


class control_event_message_data_t(ctypes.Structure):
    _fields_ = [
        ("event", ctypes.c_uint8),
        ("mode", ctypes.c_uint8),
        ("config", bilbo_control_configuration_ll_t),
        ("tick", ctypes.c_uint32)
    ]

class BILBO_Control_Event_Message(SerialMessage):
    module = 1
    address = BILBO_LL_MESSAGE_CONTROL_EVENT
    command = SerialCommandType.UART_CMD_EVENT
    data_type = control_event_message_data_t

# ======================================================================================================================
BILBO_SERIAL_MESSAGES = [BILBO_Debug_Message, BILBO_Sequencer_Event_Message, BILBO_Control_Event_Message]
