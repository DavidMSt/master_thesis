import os
import sys

from hardware.shields.bilbo_shield_rev2 import generate_shield_config

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Go up one or more levels as needed
top_level_module = os.path.abspath(os.path.join(current_dir, '..'))  # adjust as needed

if top_level_module not in sys.path:
    sys.path.insert(0, top_level_module)

from hardware.board_config import generate_board_config
from hardware.stm32.firmware_update import compileSTM32Flash
from paths import settings_file_path, robot_path
from robot.control.bilbo_control_config import generate_default_config
from robot.hardware import generate_hardware_definition
from core.utils.files import fileExists, createFile
from core.utils.json_utils import readJSON, writeJSON


# ----------------------------------------------------------------------------------------------------------------------
def write_settings_file(robot_id, board_revision, hardware_config):
    if fileExists(settings_file_path):
        data = readJSON(settings_file_path)

    else:
        data = {}

    data['ID'] = robot_id
    data['board_rev'] = board_revision
    data['hardware_config'] = hardware_config

    writeJSON(settings_file_path, data)

    if not fileExists(f"{robot_path}/{robot_id}"):
        createFile(f"{robot_path}/{robot_id}")


# ----------------------------------------------------------------------------------------------------------------------
def setup_interactive():
    robot_id = None
    board_rev = None
    hardware_config = None

    user_input_settings = False

    # 1. Check if there is a settings file
    if fileExists(settings_file_path):
        settings = readJSON(settings_file_path)
        robot_id = settings['ID']
        board_rev = settings.get('board_rev', None)
        hardware_config = settings.get('hardware_config', None)
        print(f"Setup already done: ID: {robot_id}, Size: {hardware_config}, Board Rev: {board_rev}")
        answer = input("Do you want to run setup with these settings? (y/n): ")
        if answer.lower() != 'y':
            user_input_settings = True
    else:
        user_input_settings = True

    if user_input_settings:
        # 1. Generate Board Config
        board_rev = input("Enter the board revision ('3', '4', '4.1'): ")
        if board_rev not in ('3', '4', '4.1'):
            raise ValueError("Invalid board revision")

        # 2. Generate Hardware Config
        hardware_config = input("Enter the hardware config ('small', 'normal', 'big'): ")
        if hardware_config not in ('small', 'normal', 'big'):
            raise ValueError("Invalid hardware config")

        # 3. Generate ID:
        robot_id = input("Enter the robot ID: ")

    write_settings_file(robot_id, board_rev, hardware_config)


    if board_rev is not None:
        generate_board_config(f'rev{board_rev}')
        print(f"Board config generated for revision {board_rev}")

    if hardware_config is not None:
        generate_hardware_definition(size=hardware_config)
        print(f"Hardware config generated for size {hardware_config}")

    # 4. Generate Control Config
    generate_default_config(hardware_config)
    print(f"Default control config generated for size {hardware_config}")

    # Compile stm32 flash
    compileSTM32Flash()

    print(f"Setup Complete: ID: {robot_id}, Size: {hardware_config}, Board Rev: {board_rev}")


# ----------------------------------------------------------------------------------------------------------------------
def setup(board_rev=None, hardware_config=None, robot_id=None):
    # Check if a settings file exist
    if fileExists(settings_file_path):
        settings = readJSON(settings_file_path)
        robot_id = settings.get('ID', None) if robot_id is None else robot_id
        board_rev = settings.get('board_rev', None) if board_rev is None else board_rev
        hardware_config = settings.get('hardware_config', None) if hardware_config is None else hardware_config

    if robot_id is None:
        raise ValueError("Robot ID is required")
    if board_rev is None:
        raise ValueError("Board revision is required")
    if hardware_config is None:
        raise ValueError("Hardware config is required")

    # 1. Check the inputs
    if board_rev not in ('3', '4', '4.1'):
        print("Invalid board revision")
        return

    if hardware_config not in ('small', 'normal', 'big'):
        print("Invalid hardware config")
        return

    generate_board_config(f'rev{board_rev}')
    generate_hardware_definition(size=hardware_config)
    generate_default_config(hardware_config)
    write_settings_file(robot_id, board_rev, hardware_config)

    # Compile stm32 flash
    compileSTM32Flash()

    # Generate shield configs
    generate_shield_config()

    print(f"Setup Complete: ID: {robot_id}, Size: {hardware_config}, Board Rev: {board_rev}")


# ----------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    # If command-line arguments are provided, expect exactly three:
    # board_rev, hardware_config, robot_id.
    if len(sys.argv) > 1:
        if len(sys.argv) == 4:
            board_rev, hardware_config, robot_id = sys.argv[1:4]
            setup(board_rev, hardware_config, robot_id)
        else:
            print("Invalid number of arguments")
    else:
        setup_interactive()
