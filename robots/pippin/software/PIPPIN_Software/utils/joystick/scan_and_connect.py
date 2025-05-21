from utils.joystick.joystick_utils import scan_and_connect

if __name__ == '__main__':
    result = scan_and_connect(pattern='8BitDo')
    print(result)
