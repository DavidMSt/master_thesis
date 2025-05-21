import time

from utils.joystick.joystick import JoystickManager, Joystick

used_joystick: Joystick = None


def button_callback(button, *args, **kwargs):
    print("Button callback")


def callback_new_js(joystick, *args, **kwargs):
    print(f"New joystick: {joystick}")
    global used_joystick
    used_joystick = joystick
    used_joystick.setButtonCallback(0, 'down', button_callback, parameters={'button': 0})


def callback_js_dc(joystick, *args, **kwargs):
    print("Joystick disconnected")
    global used_joystick
    used_joystick = None


def main():
    jm = JoystickManager()
    jm.callbacks.register('new_joystick', callback_new_js)
    jm.callbacks.register('joystick_disconnected', callback_js_dc)
    jm.init()
    jm.start()

    while True:
        if used_joystick is not None:
            ...
            print(used_joystick.axis[0])
        time.sleep(0.1)


if __name__ == '__main__':
    main()
