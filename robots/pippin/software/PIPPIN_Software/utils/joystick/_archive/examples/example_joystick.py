import json

import utils.joystick._archive.joystick as joystick
import time

js = joystick.Joystick()
print_axes = True


def button_pressed(button, strength, duration):
    print(f"Button {button} event")
    js.rumble(strength=strength, duration=duration)


def main():
    with open('../Mappings/mapping_SN30_Pro_Plus.json') as map_file:
        button_map = json.load(map_file)

    js.set_callback(callback_type='button', button=button_map["A"], callback=button_pressed,
                    arguments={'button': "A", 'strength': 0.2, 'duration': 0.5})
    js.set_callback(callback_type='button', button=button_map["B"], callback=button_pressed,
                    arguments={'button': "B", 'strength': 0.4, 'duration': 0.5})
    js.set_callback(callback_type='button', button=button_map["X"], callback=button_pressed,
                    arguments={'button': "X", 'strength': 0.6, 'duration': 0.5})
    js.set_callback(callback_type='button', button=button_map["Y"], callback=button_pressed,
                    arguments={'button': "Y", 'strength': 0.8, 'duration': 0.5})

    try:
        while True:
            time.sleep(0.1)
            if print_axes:
                print(js.axis)
    except KeyboardInterrupt:
        js.close()

    time.sleep(1)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
