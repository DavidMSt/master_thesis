from evdev import InputDevice, list_devices, ecodes
import time
import select
import pyudev


# def monitor_gamepad(device_name="8BitDo SN30 Pro+"):
#     """
#     Monitors if a specific gamepad is connected and reports disconnections.
#
#     Parameters:
#         device_name (str): Name of the gamepad to monitor.
#     """
#     connected_device = None
#
#     while True:
#         try:
#             # Check all devices to find the target device
#             devices = [InputDevice(path) for path in list_devices()]
#             gamepad = None
#
#             for device in devices:
#                 if device.name == device_name:
#                     gamepad = device
#                     break
#
#             if gamepad:
#                 if connected_device is None:
#                     print(f"Gamepad '{device_name}' connected at {gamepad.path}.")
#                     connected_device = gamepad
#
#             elif connected_device:
#                 print(f"Gamepad '{device_name}' disconnected.")
#                 connected_device = None
#
#         except Exception as e:
#             print(f"Error while monitoring gamepad: {e}")
#
#         # Check every second
#         time.sleep(1)


# def monitor_gamepad(device_name="8BitDo SN30 Pro+"):
#     """
#     Monitor connection and disconnection of a specific gamepad using pyudev.
#
#     Parameters:
#         device_name (str): The name of the gamepad to monitor.
#     """
#     # Set up the udev context
#     context = pyudev.Context()
#
#     # Create a monitor to listen for events on input devices
#     monitor = pyudev.Monitor.from_netlink(context)
#     monitor.filter_by('input')
#
#     print(f"Monitoring for gamepad '{device_name}'...")
#
#     # Start listening for device events
#     for device in iter(monitor.poll, None):
#         try:
#             # Check for "add" (connection) events
#             if device.action == "add":
#                 if device.get("NAME") == f'"{device_name}"':
#                     print(f"Gamepad '{device_name}' connected at {device.device_path}.")
#
#             # Check for "remove" (disconnection) events
#             elif device.action == "remove":
#                 if device.get("NAME") == f'"{device_name}"':
#                     print(f"Gamepad '{device_name}' disconnected from {device.device_path}.")
#         except Exception as e:
#             print(f"Error while processing event: {e}")

def find_joystick_device(device_name="8BitDo SN30 Pro+"):
    """
    Finds the /dev/input device corresponding to a joystick.
    Returns:
        str: Path to the joystick device file, or None if not found.
    """
    devices = [InputDevice(path) for path in list_devices()]
    for device in devices:
        # Check if the device name matches the joystick
        if device.name == device_name:
            print(f"Joystick found: {device.name} at {device.path}")
            return device.path
    print("No joystick found.")
    return None


def monitor_gamepad(device_name="8BitDo SN30 Pro+", inactivity_threshold=2.0):
    """
    Polls the gamepad for activity and detects disconnection or inactivity.

    Parameters:
        device_name (str): The name of the gamepad to monitor.
        inactivity_threshold (float): Time in seconds to wait before assuming the gamepad is inactive.
    """
    device_path = find_joystick_device(device_name)
    if not device_path:
        print(f"Gamepad '{device_name}' not found.")
        return

    print(f"Monitoring gamepad: {device_name} at {device_path}")
    device = InputDevice(device_path)
    last_event_time = time.time()

    try:
        while True:
            # Use select to wait for input with a timeout
            r, _, _ = select.select([device.fd], [], [], 0.1)  # 0.1 second timeout
            if r:
                for event in device.read():
                    last_event_time = time.time()  # Update the last event timestamp
            else:
                # No events received; check inactivity threshold
                if time.time() - last_event_time > inactivity_threshold:
                    print(f"Gamepad '{device_name}' disconnected or inactive.")
                    break

    except OSError:
        print(f"Gamepad '{device_name}' disconnected (OS error).")
    except Exception as e:
        print(f"Error while monitoring gamepad: {e}")


if __name__ == "__main__":
    monitor_gamepad(device_name="8BitDo SN30 Pro+", inactivity_threshold=2.0)