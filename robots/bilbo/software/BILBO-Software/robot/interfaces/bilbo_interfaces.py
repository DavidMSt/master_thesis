import enum
import threading
import time

# === CUSTOM PACKAGES ==================================================================================================
from core.utils.joystick.joystick_manager import JoystickManager, Joystick
from core.utils.logging_utils import Logger
from robot.bilbo_core import BILBO_Core
from robot.communication.bilbo_communication import BILBO_Communication
from robot.control.bilbo_control import BILBO_Control
from robot.interfaces.joystick import BILBO_Joystick
from core.utils.exit import register_exit_callback


# ======================================================================================================================
class InputSource(enum.Enum):
    NONE = 'NONE'
    JOYSTICK = 'JOYSTICK'
    APP = 'APP'
    EXTERNAL = 'EXTERNAL'


# ======================================================================================================================
JOYSTICK_MAPPING = {
    'CONTROL_MODE_BALANCING': "A",
    'CONTROL_MODE_OFF': "B",
    "TIC_ENABLE": "DPAD_UP",
    "TIC_DISABLE": "DPAD_DOWN",
    "AXIS_TORQUE_FORWARD": "LEFT_VERTICAL",
    "AXIS_TORQUE_TURN": "RIGHT_HORIZONTAL",
    "ACCEPT": "DPAD_RIGHT",
    "CANCEL": "DPAD_LEFT"
}


# ======================================================================================================================
class BILBO_Interfaces:
    joystick: BILBO_Joystick
    app: None

    communication: BILBO_Communication

    input_source: InputSource

    _joystick: Joystick
    _joystick_manager: JoystickManager
    _joystick_thread: threading.Thread
    _exit_joystick_task: bool

    def __init__(self, core: BILBO_Core, communication: BILBO_Communication, control: BILBO_Control):

        self.core = core
        self.communication = communication
        self.control = control

        self._joystick_manager = JoystickManager(accept_unmapped_joysticks=False)
        self._joystick_manager.callbacks.new_joystick.register(self._onJoystickConnected)
        self._joystick_manager.callbacks.joystick_disconnected.register(self._onJoystickDisconnected)

        self.logger = Logger('interfaces')
        self.logger.setLevel('DEBUG')

        self._joystick = None  # type: ignore

        # Add a hook function for the external control to hook into
        # self.communication.wifi.addCommand(identifier='setBalancingInput')

        self._joystick_thread = None  # type: ignore
        self._exit_joystick_task = False

        self.input_source = InputSource.JOYSTICK

        register_exit_callback(self.close)

    # ------------------------------------------------------------------------------------------------------------------
    def init(self):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def start(self):
        self.logger.info('Start Interfaces')
        self._joystick_manager.start()

    # ------------------------------------------------------------------------------------------------------------------
    def close(self):
        self._exit_joystick_task = True
        if self._joystick_thread is not None and self._joystick_thread.is_alive():
            self._joystick_thread.join()
        # self._joystick_manager.exit()
        self.logger.info('Stop Interfaces')

    # === PRIVATE METHODS ==============================================================================================
    def _onJoystickConnected(self, joystick, *args, **kwargs):
        self.logger.info(f'Joystick connected: {joystick.name}')
        self._joystick = joystick
        joystick.setButtonCallback(button="A", event='down', function=self._onJoystickPress)
        joystick.setButtonCallback(button="B", event='down', function=self._onJoystickPress)
        joystick.setButtonCallback(button="X", event='down', function=self._onJoystickPress)
        joystick.setButtonCallback(button="Y", event='down', function=self._onJoystickPress)

        joystick.setButtonCallback(button="DPAD_UP", event='down', function=self._onJoystickPress)
        joystick.setButtonCallback(button="DPAD_DOWN", event='down', function=self._onJoystickPress)

        joystick.setButtonCallback(button=JOYSTICK_MAPPING['ACCEPT'], event='down', function=self._onJoystickPress)
        joystick.setButtonCallback(button=JOYSTICK_MAPPING['CANCEL'], event='down', function=self._onJoystickPress)

        self_joystick_thread = threading.Thread(target=self._joystickTask, daemon=True)
        self_joystick_thread.start()

    # ------------------------------------------------------------------------------------------------------------------
    def _onJoystickDisconnected(self, joystick, *args, **kwargs):
        if joystick == self._joystick:
            self._joystick = None  # type: ignore
            joystick.clearAllButtonCallbacks()
            self.logger.info(f'Joystick disconnected: {joystick.name}')

            if self._joystick_thread is not None and self._joystick_thread.is_alive():
                self._exit_joystick_task = True
                self._joystick_thread.join()
                self._joystick_thread = None  # type: ignore

    # ------------------------------------------------------------------------------------------------------------------
    def _onJoystickPress(self, button=None, *args, **kwargs):
        self.logger.debug(f'Joystick button pressed: {button}')
        if button == JOYSTICK_MAPPING['CONTROL_MODE_BALANCING']:
            self.control.setMode(self.control.mode.BALANCING)
        elif button == JOYSTICK_MAPPING['CONTROL_MODE_OFF']:
            self.control.setMode(self.control.mode.OFF)
        elif button == JOYSTICK_MAPPING['TIC_ENABLE']:
            self.control.enableTIC(True)
        elif button == JOYSTICK_MAPPING['TIC_DISABLE']:
            self.control.enableTIC(False)
        elif button == JOYSTICK_MAPPING['ACCEPT']:
            self.logger.debug('Joystick button pressed: ACCEPT')
        elif button == JOYSTICK_MAPPING['CANCEL']:
            self.logger.debug('Joystick button pressed: CANCEL')
        else:
            self.logger.debug(f'Joystick button pressed: {button} not recognized')
            return

    # ------------------------------------------------------------------------------------------------------------------
    def _joystickTask(self):

        while self._joystick is not None and not self._exit_joystick_task:

            axis_forward = - self._joystick.getAxis(JOYSTICK_MAPPING['AXIS_TORQUE_FORWARD'])
            axis_turn = -self._joystick.getAxis(JOYSTICK_MAPPING['AXIS_TORQUE_TURN'])

            if self.input_source == InputSource.JOYSTICK:
                self.control.setNormalizedBalancingInput(axis_forward, axis_turn)

            time.sleep(0.1)
