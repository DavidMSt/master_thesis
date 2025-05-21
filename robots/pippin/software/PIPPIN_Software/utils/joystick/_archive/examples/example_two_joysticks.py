import logging
import time

from scioi_py_core.utils.joystick.joystick_manager import JoystickManager

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d  %(levelname)-8s  %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


def callback_js_1():
    print("JS1")


def callback_js_2():
    print("JS2")


def main():
    jm = JoystickManager(required_sticks=2)

    jm.joysticks[0].set_callback('button', 0, callback_js_1, {})
    jm.joysticks[1].set_callback('button', 0, callback_js_2, {})

    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
