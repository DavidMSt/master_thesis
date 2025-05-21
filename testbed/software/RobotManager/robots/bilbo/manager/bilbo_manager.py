from core.device_manager import DeviceManager
from core.device import Device
from robots.bilbo.manager.bilbo_manager_cli import BILBO_Manager_CommandSet
from core.utils.callbacks import callback_definition, CallbackContainer
from robots.bilbo.robot.bilbo import BILBO
from robots.bilbo.robot.bilbo_definitions import BILBO_Control_Mode, TWIPR_IDS, TWIPR_PASSWORD, TWIPR_REMOTE_START_COMMAND, \
    TWIPR_USER_NAME, TWIPR_REMOTE_STOP_COMMAND
from robots.bilbo.manager.robotscanner import RobotScanner
from core.utils.time import delayed_execution
from core.utils.exit import register_exit_callback
from core.utils.logging_utils import Logger
from core.utils.network.ssh import executeCommandOverSSH

# === GLOBAL VARIABLES =================================================================================================
logger = Logger('ROBOT MANAGER')
logger.setLevel('INFO')


# ======================================================================================================================
@callback_definition
class TWIPR_Manager_Callbacks:
    new_robot: CallbackContainer
    robot_disconnected: CallbackContainer
    stream: CallbackContainer


# ======================================================================================================================
class BILBO_Manager:
    """
    Manages the connection and control of BILBO robots using the DeviceManager.
    Handles device events and provides methods to interact with connected robots.
    """

    deviceManager: DeviceManager
    callbacks: TWIPR_Manager_Callbacks
    robots: dict[str, BILBO]

    robot_auto_start: bool
    network_scanner: RobotScanner = None

    def __init__(self, robot_auto_start=True):
        """
        Initializes the TWIPR_Manager instance by setting up the device manager,
        registering callbacks, and initializing internal dictionaries for robots and callbacks.
        """
        self.deviceManager = DeviceManager()
        self.deviceManager.callbacks.new_device.register(self._newDevice_callback)
        self.deviceManager.callbacks.device_disconnected.register(self._deviceDisconnected_callback)
        self.deviceManager.callbacks.stream.register(self._deviceStream_callback)

        self.robots = {}

        self.callbacks = TWIPR_Manager_Callbacks()

        self.scanner = None
        self.robot_auto_start = robot_auto_start
        if self.robot_auto_start:
            self.scanner = RobotScanner(TWIPR_IDS)
            self.scanner.callbacks.found.register(self._scannerRobotFound_callback)
            self.scanner.callbacks.lost.register(self._scannerRobotLost_callback)

        # Command Set
        self.cli_command_set = BILBO_Manager_CommandSet(self)

        # Exit Handler
        register_exit_callback(self.close)

    @property
    def connected_robots(self):
        """
        Returns the number of connected robots.
        :return: Number of connected robots
        """
        return len(self.robots)

    # ------------------------------------------------------------------------------------------------------------------
    def init(self):
        """
        Initializes the twipr manager.
        """
        self.deviceManager.init()

    # ------------------------------------------------------------------------------------------------------------------
    def start(self):
        """
        Starts the BILBO Manager by initiating the device manager.
        """
        logger.info('Starting BILBO Manager')
        self.deviceManager.start()
        if self.scanner is not None:
            self.scanner.start()

    # ------------------------------------------------------------------------------------------------------------------
    def close(self, *args, **kwargs):
        logger.info("Close BILBO Manager")
        if self.scanner is not None:
            active_robots = self.scanner.active_robots
            for name, address in active_robots.items():
                self._stopTWIPRRemote(name, address)

    # ------------------------------------------------------------------------------------------------------------------
    def getRobotById(self, robot_id):
        """
        Retrieves a robot instance by its ID.

        :param robot_id: ID of the robot to retrieve
        :return: BILBO robot instance if found, None otherwise
        """
        if robot_id not in self.robots.keys():
            logger.warning(f"No robot with id {robot_id} is connected.")
            return None

        return self.robots[robot_id]

    # ------------------------------------------------------------------------------------------------------------------
    def emergencyStop(self):
        """
        Issues an emergency stop command to all connected robots.
        """
        logger.warning("Emergency Stop")
        for robot in self.robots.values():
            robot.control.setControlMode(BILBO_Control_Mode.OFF)

    # ------------------------------------------------------------------------------------------------------------------
    def setRobotControlMode(self, robot, mode):
        """
        Sets the control mode of a specified robot.

        :param robot: Robot instance or robot ID
        :param mode: Control mode to set (either as a string or an integer)
        """
        if isinstance(robot, str):
            if robot in self.robots.keys():
                robot = self.robots[robot]
            else:
                return

        if isinstance(mode, str):
            control_mode_dict = {"off": 0, "direct": 1, "balancing": 2, "speed": 3}
            if mode in control_mode_dict.keys():
                mode = control_mode_dict[mode]
            else:
                return

        robot.setControlMode(mode)

    # ------------------------------------------------------------------------------------------------------------------
    def _newDevice_callback(self, device: Device, *args, **kwargs):
        """
        Callback for handling new device connections.

        :param device: The newly connected device
        """
        # Check if the device has the correct class and type
        if not (device.information.device_class == 'robot' and device.information.device_type == 'bilbo'):

            if device.information.device_class == 'robot':
                logger.warning(f"Robot attempted to connect with type {device.information.device_type}")
            return

        robot = BILBO(device)

        # Check if this robot ID is already used
        if robot.device.information.device_id in self.robots.keys():
            logger.warning(f"New Robot connected, but ID {robot.device.information.device_id} is already in use")

        self.robots[robot.device.information.device_id] = robot

        self.cli_command_set.addChild(robot.interfaces.cli_command_set)

        logger.info(f"New Robot connected with ID: \"{robot.device.information.device_id}\"")

        for callback in self.callbacks.new_robot:
            callback(robot, *args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------
    def _deviceDisconnected_callback(self, device, *args, **kwargs):
        """
        Callback for handling device disconnections.

        :param device: The disconnected device
        """
        if device.information.device_id not in self.robots:
            return

        robot = self.robots[device.information.device_id]
        self.robots.pop(device.information.device_id)

        logger.warning(f"Robot {device.information.device_id} disconnected")

        # Remove the CLI Command Set
        self.cli_command_set.removeChild(robot.interfaces.cli_command_set)

        for callback in self.callbacks.robot_disconnected:
            callback(robot, *args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------
    def _deviceStream_callback(self, stream, device, *args, **kwargs):
        """
        Callback for handling data streams from devices.

        :param stream: The data stream
        :param device: The device sending the stream
        """
        if device.information.device_id in self.robots.keys():
            for callback in self.callbacks.stream:
                callback(stream, self.robots[device.information.device_id], *args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------
    def _scannerRobotFound_callback(self, name, ip_address, *args, **kwargs):
        logger.info(f"Scanner found robot {name} with IP address {ip_address}")
        self._startTWIPRRemote(name, ip_address)

    # ------------------------------------------------------------------------------------------------------------------
    def _scannerRobotLost_callback(self, name, ip_address, *args, **kwargs):
        logger.info(f"Scanner lost robot {name} with IP address {ip_address}")

    # ------------------------------------------------------------------------------------------------------------------
    def _startTWIPRRemote(self, name, ip_address, *args, **kwargs):
        logger.info(f"Starting {name} remotely via ssh")
        delayed_execution(executeCommandOverSSH, delay=0.25, hostname=ip_address,
                          username=TWIPR_USER_NAME,
                          password=TWIPR_PASSWORD,
                          command=TWIPR_REMOTE_STOP_COMMAND)

        delayed_execution(executeCommandOverSSH, delay=2, hostname=ip_address,
                          username=TWIPR_USER_NAME,
                          password=TWIPR_PASSWORD,
                          command=TWIPR_REMOTE_START_COMMAND)

    # ------------------------------------------------------------------------------------------------------------------
    def _stopTWIPRRemote(self, name, ip_address, *args, **kwargs):
        logger.info(f"Stopping {name} remotely via ssh")
        executeCommandOverSSH(hostname=ip_address,
                              username=TWIPR_USER_NAME,
                              password=TWIPR_PASSWORD,
                              command=TWIPR_REMOTE_STOP_COMMAND)
