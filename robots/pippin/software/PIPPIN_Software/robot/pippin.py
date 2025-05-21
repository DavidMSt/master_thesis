import threading
import time
from PIL import Image

from robot.lib.LCD_2inch import LCD_2inch
from robot.lib.xgolib import XGO
from utils.files import relativeToFullPath
from utils.joystick.joystick import JoystickManager, Joystick
from utils.logging_utils import Logger


class Pippin:
    _xgo: XGO

    joystick: Joystick
    _joystick_manager: JoystickManager
    _joystick_thread: threading.Thread
    _exit_joystick_thread: bool

    def __init__(self):
        self._xgo = XGO('xgorider')

        self._joystick_manager = JoystickManager()
        self._joystick_manager.callbacks.new_joystick.register(self._onNewJoystick)
        self._joystick_manager.callbacks.joystick_disconnected.register(self._onJoystickDisconnect)
        self.joystick = None  # type: ignore

        self.logger = Logger("Pippin")
        self.logger.setLevel('INFO')

        self._exit_joystick_thread = False
        self._joystick_thread = None  # type: ignore

        self.lcd = LCD_2inch()
        self.lcd.Init()

    def start(self):
        self.reset()
        self._joystick_manager.start()
        self.logger.info("Pippin started!")

        img = Image.open(relativeToFullPath('./lib/imes.png'))
        img = img.resize((self.lcd.height, self.lcd.width))  # rotate if you like
        self.lcd.ShowImage(img)

    def reset(self):
        self._xgo.rider_reset()

    def move(self, forward=0, turn=0):
        forward = self._map_value(forward, -1, 1, -5, 5)
        turn = self._map_value(turn, -1, 1, -300, 300)
        self._xgo.rider_move_x(forward)
        self._xgo.rider_turn(turn)

    def setHeight(self, height: float):
        height = self._map_value(height, 0, 1, -255, 200)
        self._xgo.rider_height(height)

    def setRoll(self, roll: float):
        roll = self._map_value(roll, -1, 1, -20, 20)
        self._xgo.rider_roll(roll)

    @staticmethod
    def _map_value(value, from_low, from_high, to_low, to_high):
        return (value - from_low) * (to_high - to_low) / (from_high - from_low) + to_low

    def _onNewJoystick(self, joystick):
        if self.joystick is not None:
            return

        self.joystick = joystick
        self.joystick.setButtonCallback(0, 'down', self.reset)
        self.logger.info(f"New Joystick connected: {joystick.name}")

        self._joystick_thread = threading.Thread(target=self._joystick_task, daemon=True)
        self._joystick_thread.start()

    def _onJoystickDisconnect(self, joystick):
        if joystick == self.joystick:
            self.logger.warning(f"Joystick disconnected: {joystick.name}")
            self.joystick = None  # type: ignore
            self.move(0, 0)
            self._exit_joystick_thread = True
            self._joystick_thread.join()
            self._exit_joystick_thread = False
            self._joystick_thread = None  # type: ignore

    def _joystick_task(self):
        while not self._exit_joystick_thread:
            if self.joystick is not None:
                axis_forward = -self.joystick.axis[1]
                axis_turn = -self.joystick.axis[3]
                axis_height = self.joystick.axis[2]
                axis_roll = self.joystick.axis[0]
                self.setHeight(self._map_value(axis_height, -1, 1, 1, 0))
                self.move(axis_forward, axis_turn)
                # self.setRoll(axis_roll)
            else:
                self.move(0, 0)

            time.sleep(0.1)
