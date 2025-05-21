import dataclasses
import enum


class BILBO_Control_Mode(enum.IntEnum):
    OFF = 0,
    DIRECT = 1,
    BALANCING = 2,
    VELOCITY = 3,

@dataclasses.dataclass
class TIC_Config:
    enabled: bool = False
    ki: float = 0.0
    max_error: float = 0.0
    theta_limit: float = 0.0


@dataclasses.dataclass
class VIC_Config:
    enabled: bool = False
    ki: float = 0.0
    max_error: float = 0.0
    v_limit: float = 0.0


@dataclasses.dataclass
class TWIPR_Balancing_Control_Config:
    K: list = dataclasses.field(default_factory=list)  # State Feedback Gain
    tic: TIC_Config = dataclasses.field(default_factory=TIC_Config)
    vic: VIC_Config = dataclasses.field(default_factory=VIC_Config)


@dataclasses.dataclass
class TWIPR_PID_Control_Config:
    Kp: float = 0.0
    Kd: float = 0.0
    Ki: float = 0.0
    # anti_windup: float = 0
    # integrator_saturation: float = None


@dataclasses.dataclass
class SpeedControl_Config:
    v: TWIPR_PID_Control_Config = dataclasses.field(default_factory=TWIPR_PID_Control_Config)
    psidot: TWIPR_PID_Control_Config = dataclasses.field(default_factory=TWIPR_PID_Control_Config)
    max_speeds: dict = dataclasses.field(default_factory=dict)

@dataclasses.dataclass
class General_Control_Config:
    max_wheel_speed: float = 0.0
    max_wheel_torque: float = 0.0
    enable_external_inputs: bool = False
    torque_offset: dict =  dataclasses.field(default_factory=lambda: {'left': 0, 'right': 0})


@dataclasses.dataclass
class ExternalInputsConfig:
    balancing_input_gain: dict = dataclasses.field(default_factory=dict)  # 'forward' and 'turn'
    speed_input_gain: dict = dataclasses.field(default_factory=dict)  # 'forward' and 'turn'


@dataclasses.dataclass
class BILBO_ControlConfig:
    name: str = ''
    description: str = ''
    mode: BILBO_Control_Mode = dataclasses.field(default=BILBO_Control_Mode(BILBO_Control_Mode.OFF))
    general: General_Control_Config = dataclasses.field(default_factory=General_Control_Config)
    external_inputs: ExternalInputsConfig = dataclasses.field(default_factory=ExternalInputsConfig)
    balancing_control: TWIPR_Balancing_Control_Config = dataclasses.field(
        default_factory=TWIPR_Balancing_Control_Config)
    speed_control: SpeedControl_Config = dataclasses.field(default_factory=SpeedControl_Config)





class BILBO_Control_Status(enum.IntEnum):
    ERROR = 0
    NORMAL = 1


@dataclasses.dataclass
class BILBO_Control_Input_Direct:
    u_left: float = 0.0
    u_right: float = 0.0


@dataclasses.dataclass
class BILBO_Control_Input_Balancing:
    u_left: float = 0.0
    u_right: float = 0.0


@dataclasses.dataclass
class BILBO_Control_Input_Velocity:
    forward: float = 0.0
    turn: float = 0.0


@dataclasses.dataclass
class BILBO_Control_Input:
    direct: BILBO_Control_Input_Direct = dataclasses.field(default_factory=BILBO_Control_Input_Direct)
    balancing: BILBO_Control_Input_Balancing = dataclasses.field(default_factory=BILBO_Control_Input_Balancing)
    velocity: BILBO_Control_Input_Velocity = dataclasses.field(default_factory=BILBO_Control_Input_Velocity)


@dataclasses.dataclass(frozen=True)
class TWIPR_Control_Sample:
    status: BILBO_Control_Status = dataclasses.field(
        default=BILBO_Control_Status(BILBO_Control_Status.ERROR)
    )
    mode: BILBO_Control_Mode = dataclasses.field(default=BILBO_Control_Mode(BILBO_Control_Mode.OFF))
    configuration: str = ''
    input: BILBO_Control_Input = dataclasses.field(default_factory=BILBO_Control_Input)


class BILBO_Control_Event_Type(enum.IntEnum):
    ERROR = 0
    MODE_CHANGED = 1
    CONFIGURATION_CHANGED = 2