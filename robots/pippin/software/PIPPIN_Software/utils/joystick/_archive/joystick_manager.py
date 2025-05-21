import ctypes
import logging
from typing import Dict, Tuple, Optional, Union, Sequence, Iterable, Iterator
import threading
import pygame
import time

# source code from SO
# https://stackoverflow.com/questions/19749404/is-it-possible-to-rumble-a-xbox-360-controller-with-python
switchRumble = 0


# Define necessary structures
class XInputVibration(ctypes.Structure):
    _fields_ = [("wLeftMotorSpeed", ctypes.c_ushort),
                ("wRightMotorSpeed", ctypes.c_ushort)]


# Load XInput.dll (-> change version number if needed (C:\Windows\System32\XInput1_<version number>))
# Or download the .dll file from the internet, it's the MICROSOFT COMMON CONTROLLER API
# 22.07.2021: newest version == 4
XInput = ctypes.windll.xinput1_4

# Set up function argument types and return type
XInputSetState = XInput.XInputSetState
XInputSetState.argtypes = [ctypes.c_uint, ctypes.POINTER(XInputVibration)]
XInputSetState.restype = ctypes.c_uint

registered_joysticks = 0


# My Imports

def sign(x):
    return x and (1, -1)[x < 0]


class JoystickButton:
    time_pressed: float
    pressed: bool
    id: int
    name: str

    def __init__(self):
        pass


class JoystickManager:
    joysticks: list['Joystick']

    _thread: threading.Thread
    _exit: bool

    _last_count: int

    def __init__(self, required_sticks: int = 0):

        self.joysticks = []
        for i in range(0, required_sticks):
            self.joysticks.append(Joystick())

        self._last_count = 0

        self._exit = False
        self._thread = threading.Thread(target=self._thread_fun, daemon=True)
        self._thread.start()

    def exit(self):
        self._exit = True

    def switchRumble(self):
        global switchRumble
        if switchRumble == 0:
            switchRumble = 1
        else:
            switchRumble = 0

    def _thread_fun(self):
        pygame.init()
        pygame.joystick.init()

        while not self._exit:

            # Check if a new joystick is added
            joystick_count = pygame.joystick.get_count()
            if joystick_count > self._last_count:
                self._last_count = joystick_count
                for i in range(0, pygame.joystick.get_count()):
                    js = pygame.joystick.Joystick(i)
                    if not (js.get_instance_id() in [js.id for js in self.joysticks]):
                        print(f"New Joystick with id {js.get_instance_id()}")

                        unregistered_joystick = next((j for j in self.joysticks if j.connected is False), None)
                        if unregistered_joystick is not None:
                            unregistered_joystick.register(js)
                        else:
                            new_joystick = Joystick()
                            new_joystick.register(js)
                            self.joysticks.append(new_joystick)
            # Events
            for event in pygame.event.get():
                if event.type == pygame.JOYDEVICEADDED:
                    pass  # TODO
                elif event.type == pygame.JOYBUTTONDOWN:
                    # Check the id
                    id = event.instance_id

                    # Check if I have a joystick with this id
                    js = next((js for js in self.joysticks if js.id == id), None)
                    if js is not None:
                        callback = next((x for x in js.callbacks if x.datatype == 'button' and x.button == event.button),
                                        None)
                        if callback is not None:
                            callback()

                elif event.type == pygame.JOYBUTTONUP:
                    pass
                elif event.type == pygame.JOYHATMOTION:
                    pass
                elif event.type == pygame.JOYAXISMOTION:
                    pass

            time.sleep(0.001)


class Joystick:
    joystick: pygame.joystick.Joystick
    information: Dict[str, Union[int, str]]
    mapping: Dict[str, int]
    dead_band: float
    id: int
    connected: bool
    exit: bool
    axis: list
    callbacks: list

    buttons: dict  # TODO: add a button dict that stores whether a button is pressed and for how long

    _exit: bool

    _enable_rumble: bool
    _rumble_time: int

    # === INIT =========================================================================================================
    def __init__(self, Ts: float = 0.04) -> None:
        """

        :param Ts:
        """
        self.connected = False
        self.axis = [0, 0, 0, 0, 0, 0]
        self.Ts = Ts
        self.callbacks = []

        self.id = -1

        self._exit = False
        self._enable_rumble = False
        self._rumble_time = 0

        thread = threading.Thread(target=self._thread_fun, daemon=True)
        thread.start()

    # === METHODS ======================================================================================================
    def register(self, joystick: pygame.joystick.Joystick):
        self.joystick = joystick
        self.id = joystick.get_instance_id()
        self.connected = True

    def set_callback(self, callback_type, button, callback, arguments):
        """

        :param callback_type:
        :param button:
        :param callback:
        :param kwargs:
        :return:
        """
        self.callbacks.append(JoystickButtonCallback(callback_type, button, callback, arguments))

    # ------------------------------------------------------------------------------------------------------------------
    def close(self):
        self._exit = True

    # ------------------------------------------------------------------------------------------------------------------
    def rumble(self, strength, duration):
        if self.connected:
            if strength == 0:
                self._enable_rumble = False
                self._rumble(self.id, 0, 0)
            else:
                self._rumble(self.id, strength, strength)
                self._enable_rumble = True
                self._rumble_time = time.perf_counter_ns() + duration * 1e9

    # === PRIVATE METHODS ==============================================================================================
    def _thread_fun(self):
        """

        :return:
        """
        while not self._exit:
            self._update()
            time.sleep(0.001)

        logging.info(f"Close Joystick")

    # ------------------------------------------------------------------------------------------------------------------
    def _update(self):
        global registered_joysticks
        """

        :return:
        """

        # Axes
        if self.connected:
            axes = self.joystick.get_numaxes()
            for i in range(0, axes):
                self.axis[i] = self.joystick.get_axis(i)

            # Rumble
            if self._enable_rumble:
                if self._rumble_time < time.perf_counter_ns():
                    self._rumble(self.id, 0, 0)
                    self._enable_rumble = False

        time.sleep(self.Ts)

    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def _rumble(joystick_id, left_motor, right_motor):
        """

        :param joystick_id:
        :param left_motor:
        :param right_motor:
        :return:
        """
        global switchRumble
        vibration = XInputVibration(int(left_motor * 65535), int(right_motor * 65535))

        # # TODO: BAAAAAAAAAAD HACK
        if switchRumble:
            if joystick_id == 0:
                joystick_id = 1
            elif joystick_id == 1:
                joystick_id = 0
        XInputSetState(joystick_id, ctypes.byref(vibration))


class JoystickButtonCallback:
    """

    """

    def __init__(self, callback_type, button, function, arguments):
        """

        :param callback_type:
        :param button:
        :param function:
        :param kwargs:
        """
        self.type = callback_type
        self.button = button
        self.function = function
        self.arguments = arguments

    def __call__(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        """
        x = {**self.arguments, **kwargs}
        self.function(*args, **x)

# joystick_count = pygame.joystick.get_count()

# for i in range(joystick_count):
#     joystick = pygame.joystick.Joystick(i)
#     if joystick == self.joystick:
#         axes = joystick.get_numaxes()
#
#         for j in range(axes):
#             self.axes[j] = joystick.get_axis(j)
