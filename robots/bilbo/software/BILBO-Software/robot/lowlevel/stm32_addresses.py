import enum


class TWIPR_AddressTables(enum.IntEnum):
    REGISTER_TABLE_GENERAL = 0x01


class TWIPR_GeneralAddresses(enum.IntEnum):
    ADDRESS_FIRMWARE_STATE = 0x01
    ADDRESS_FIRMWARE_TICK = 0x02
    ADDRESS_FIRMWARE_REVISION = 0x03
    ADDRESS_FIRMWARE_DEBUG = 0x04
    ADDRESS_FIRMWARE_BEEP = 0x05
    ADDRESS_BOARD_REVISION = 0x06
    ADDRESS_FIRMWARE_EXTERNAL_LED = 0x07
    ADDRESS_FIRMWARE_DEBUG_1_FLAG = 0x08

    ADDRESS_FIRMWARE_RESET = 0xF1


class TWIPR_ControlAddresses(enum.IntEnum):
    ADDRESS_CONTROL_READ_MODE = 0x10
    ADDRESS_CONTROL_SET_MODE = 0x11
    ADDRESS_CONTROL_SET_K = 0x12
    ADDRESS_CONTROL_SET_FORWARD_PID = 0x13
    ADDRESS_CONTROL_SET_TURN_PID = 0x14
    ADDRESS_CONTROL_SET_DIRECT_INPUT = 0x15
    ADDRESS_CONTROL_SET_BALANCING_INPUT = 0x16
    ADDRESS_CONTROL_SET_SPEED_INPUT = 0x17
    ADDRESS_CONTROL_READ_CONFIG = 0x18

    SET_CONFIG = 0x19

    ADDRESS_CONTROL_RW_MAX_WHEEL_SPEED = 0x20

    ENABLE_VELOCITY_INTEGRAL_CONTROL = 0x31
    ENABLE_TIC = 0x33

class TWIPR_EstimationAddresses(enum.IntEnum):
    SET_THETA_OFFSET = 0x50

class TWIPR_SequencerAddresses(enum.IntEnum):
    LOAD = 0x21
    START = 0x22
    STOP = 0x23
    READ = 0x24
