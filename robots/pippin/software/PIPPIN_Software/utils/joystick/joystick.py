import enum
import threading
import time
from os import environ

from utils.callbacks import Callback, callback_handler, CallbackContainer
from utils.logging_utils import Logger

environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

logger = Logger('Joystick')

def sign(x):
    return x and (1, -1)[x < 0]


@callback_handler
class JoystickManager_Callbacks:
    new_joystick: CallbackContainer
    joystick_disconnected: CallbackContainer

class JoystickButton:
    time_pressed: float
    pressed: bool
    id: int
    name: str

    def __init__(self):
        pass


# ======================================================================================================================
class JoystickManager:
    joysticks: dict
    callbacks: JoystickManager_Callbacks

    _thread: threading.Thread
    _exit: bool

    _last_count: int

    def __init__(self, max_sticks: int = 5):

        self.joysticks = {}

        self.callbacks = JoystickManager_Callbacks()

        self._last_count = 0

        self._exit = False
        self._thread = threading.Thread(target=self._thread_fun, daemon=True)

        self._monitor_thread = threading.Thread(target=self._monitorJoysticks, daemon=True)
        self.monitor_interval = 1.0  # Seconds to check for inactivity
        self._last_event_time = {}

    # ------------------------------------------------------------------------------------------------------------------
    def start(self):
        self._thread.start()
        self._monitor_thread.start()

    # ------------------------------------------------------------------------------------------------------------------
    def exit(self):
        self._exit = True

    # ------------------------------------------------------------------------------------------------------------------
    def _getJoystickByInstanceId(self, instance_id) -> 'Joystick':
        joystick = None
        # Search for the joystick with this instance_id:
        for uuid, stick in self.joysticks.items():
            if stick.id == instance_id:
                joystick = self.joysticks[uuid]
                break

        return joystick

    # ------------------------------------------------------------------------------------------------------------------
    def _registerJoystick(self, device_index):
        joystick = Joystick(joystick=pygame.joystick.Joystick(device_index))
        self.joysticks[joystick.uuid] = joystick
        logger.info(f"New Joystick connected. Type: {joystick.name}. UUID: {joystick.uuid}")

        for callback in self.callbacks.new_joystick:
            callback(joystick)

    # ------------------------------------------------------------------------------------------------------------------
    def _checkJoystickState(self):
        for joystick_uuid, joystick in list(self.joysticks.items()):
            if not joystick.joystick.get_init():
                # Joystick is no longer initialized
                self._removeJoystick(joystick.id)

    # ------------------------------------------------------------------------------------------------------------------
    def _removeJoystick(self, instance_id):

        joystick = self._getJoystickByInstanceId(instance_id)
        self.joysticks.pop(joystick.uuid)

        logger.info(f"Joystick disconnected. Type: {joystick.name}. UUID: {joystick.uuid}")

        for callback in self.callbacks.joystick_disconnected:
            callback(joystick)

    # ------------------------------------------------------------------------------------------------------------------
    def _handleButtonEvent(self, event):

        # Get the Joystick for the event
        joystick = self._getJoystickByInstanceId(event.instance_id)

        # Get the button of the event
        button = event.button

        if event.type == pygame.JOYBUTTONDOWN:
            joystick._buttonDown(button)
        elif event.type == pygame.JOYBUTTONUP:
            joystick._buttonUp(button)

    # ------------------------------------------------------------------------------------------------------------------
    def _handleJoyHatEvent(self, event):
        joystick = self._getJoystickByInstanceId(event.instance_id)

        # Get the joyhat direction
        direction = None

        if event.value == (0, 1):
            direction = 'up'
        elif event.value == (1, 0):
            direction = 'right'
        elif event.value == (-1, 0):
            direction = 'left'
        elif event.value == (0, -1):
            direction = 'down'

        joystick._joyhatEvent(direction)

    # ------------------------------------------------------------------------------------------------------------------
    def _checkEvents(self):
        for event in pygame.event.get():
            if event.type == pygame.JOYDEVICEADDED:
                self._registerJoystick(event.device_index)
            elif event.type == pygame.JOYDEVICEREMOVED:
                self._removeJoystick(event.instance_id)

            elif event.type == pygame.JOYBUTTONDOWN:
                self._handleButtonEvent(event)
            elif event.type == pygame.JOYBUTTONUP:
                self._handleButtonEvent(event)
            elif event.type == pygame.JOYHATMOTION:
                self._handleJoyHatEvent(event)

            if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP, pygame.JOYHATMOTION):
                joystick = self._getJoystickByInstanceId(event.instance_id)
                if joystick:
                    self._last_event_time[joystick.uuid] = time.time()

            pygame.event.clear()

    # ------------------------------------------------------------------------------------------------------------------
    def _thread_fun(self):
        pygame.init()
        pygame.joystick.init()

        while not self._exit:
            # Events
            self._checkEvents()

            time.sleep(0.001)

    def _monitorJoysticks(self):
        time.sleep(self.monitor_interval)

    def init(self):
        pass


# ======================================================================================================================
class Joystick:
    joystick: pygame.joystick.Joystick

    id: int
    guid: str
    uuid: str
    name: str

    connected: bool
    axis: list

    num_axes: int

    button_callbacks: list['JoystickButtonCallback']
    joyhat_callbacks: list['JoyHatCallback']

    buttons: dict  # TODO: add a button dict that stores whether a button is pressed and for how long

    # === INIT =========================================================================================================
    def __init__(self, joystick: pygame.joystick = None, Ts: float = 0.04) -> None:
        """

        :param Ts:
        """
        self.connected = False
        # self.axis = [0, 0, 0, 0, 0, 0]
        self.Ts = Ts
        self.button_callbacks = []
        self.joyhat_callbacks = []

        self.id = -1
        self.num_axes = 0
        self.uuid = ''
        self.name = ''

        self._axis = []

        if joystick is not None:
            self.register(joystick)

    # === METHODS ======================================================================================================
    def register(self, joystick: pygame.joystick.Joystick):
        self.joystick = joystick
        self.id = joystick.get_instance_id()
        self.guid = self.joystick.get_guid()
        self.uuid = self.guid
        self.name = self.joystick.get_name()
        self.num_axes = self.joystick.get_numaxes()
        self._axis = [0] * self.num_axes
        self.connected = True
        self.joystick.stop_rumble()

    # ------------------------------------------------------------------------------------------------------------------
    def setButtonCallback(self, button, event: str, function: callable, parameters: dict = None, lambdas: dict = None):
        if isinstance(button, list):
            for _button in button:
                self.button_callbacks.append(JoystickButtonCallback(_button, event, function, parameters, lambdas))
        else:
            self.button_callbacks.append(JoystickButtonCallback(button, event, function, parameters, lambdas))

    # ------------------------------------------------------------------------------------------------------------------
    def clearAllButtonCallbacks(self):
        self.button_callbacks = []
        self.joyhat_callbacks = []

    # ------------------------------------------------------------------------------------------------------------------
    def setJoyHatCallback(self, direction: str, function: callable, parameters: dict = None, lambdas: dict = None):
        if isinstance(direction, list):
            for dir in direction:
                self.joyhat_callbacks.append(JoyHatCallback(dir, function, parameters, lambdas))
        else:
            self.joyhat_callbacks.append(JoyHatCallback(direction, function, parameters, lambdas))

    # ------------------------------------------------------------------------------------------------------------------
    def close(self):
        self.connected = False

    # ------------------------------------------------------------------------------------------------------------------
    def rumble(self, strength, duration):
        self.joystick.rumble(strength, strength, duration)

    # ------------------------------------------------------------------------------------------------------------------
    def _buttonDown(self, button):
        callbacks = [callback for callback in self.button_callbacks if
                     callback.button == button and callback.event == 'down']

        for callback in callbacks:
            callback()

    # ------------------------------------------------------------------------------------------------------------------
    def _buttonUp(self, button):
        callbacks = [callback for callback in self.button_callbacks if
                     callback.button == button and callback.event == 'up']

        for callback in callbacks:
            callback()

    # ------------------------------------------------------------------------------------------------------------------
    def _joyhatEvent(self, direction):
        callbacks = [callback for callback in self.joyhat_callbacks if
                     callback.direction == direction]

        for callback in callbacks:
            callback(joystick=self, direction=direction)

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def axis(self):
        if self.connected:
            for i in range(0, self.num_axes):
                self._axis[i] = self.joystick.get_axis(i)
        return self._axis


class JoyHatCallback:
    callback: Callback
    direction: str

    def __init__(self, direction, function: callable, parameters: dict = None, lambdas: dict = None):
        self.direction = direction
        self.callback = Callback(function, parameters, lambdas)

    def __call__(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        """
        self.callback(*args, **kwargs)


class JoystickButtonCallback:
    callback: Callback
    event: str

    def __init__(self, button, event, function: callable, parameters: dict = None, lambdas: dict = None):
        """

        :param callback_type:
        :param button:
        :param function:
        :param kwargs:
        """
        self.button = button
        self.event = event
        self.callback = Callback(function, parameters, lambdas)

    def __call__(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        """
        self.callback(*args, **kwargs)
