import time

# === OWN PACKAGES =====================================================================================================
from core.communication.wifi.tcp.protocols.tcp_json_protocol import TCP_JSON_Message
from core.communication.wifi.tcp.tcp_server import TCP_Server
from core.device import Device
from core.utils.callbacks import callback_definition, CallbackContainer
from core.utils.events import event_definition, ConditionEvent
from core.utils.logging_utils import Logger
from core.utils.network.network import getHostIP

# === GLOBAL VARIABLES =================================================================================================
logger = Logger('DEVICES')
logger.setLevel('INFO')


# ======================================================================================================================
@callback_definition
class DeviceManagerCallbacks:
    new_device: CallbackContainer
    device_disconnected: CallbackContainer
    stream: CallbackContainer
    event: CallbackContainer


@event_definition
class DeviceManagerEvents:
    new_device: ConditionEvent
    device_disconnected: ConditionEvent
    stream: ConditionEvent
    event: ConditionEvent


# ======================================================================================================================
class DeviceManager:
    server: TCP_Server
    devices: dict[str, Device]
    callbacks: DeviceManagerCallbacks
    events: DeviceManagerEvents

    # === INIT =========================================================================================================
    def __init__(self):

        self.devices = {}
        self.callbacks = DeviceManagerCallbacks()
        self.events = DeviceManagerEvents()

        address = getHostIP()

        if address is None:
            logger.info("No valid IP available")
            exit()

        self.address = address
        self.server = TCP_Server(address)
        self.server.callbacks.connected.register(self._newConnection_callback)
        self._unregistered_devices = []

    # === METHODS ======================================================================================================
    # ------------------------------------------------------------------------------------------------------------------
    def init(self):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def start(self):
        logger.info(f"Starting Device Manager on {self.server.address}")
        self.server.start()

    # ------------------------------------------------------------------------------------------------------------------
    def addEvent(self, event: ConditionEvent):
        ...

    # === PRIVATE METHODS ==============================================================================================
    def _newConnection_callback(self, connection):

        # Make a new generic device with the connection
        device = Device()
        device.tcp_connection = connection

        # Append this device to the unregistered devices, since it has not yet sent an identification message
        self._unregistered_devices.append(device)

        device.callbacks.registered.register(self._deviceRegistered_callback)
        device.callbacks.disconnected.register(self._deviceDisconnected_callback)

    # ------------------------------------------------------------------------------------------------------------------
    def _deviceRegistered_callback(self, device: Device):

        logger.info(
            f'New device registered. Name: {device.information.device_name} ({device.information.device_class}/{device.information.device_type})')

        self._sendSyncMessage(device)
        self.devices[device.information.device_id] = device
        self._unregistered_devices.remove(device)

        device.callbacks.stream.register(self._deviceStreamCallback)
        device.callbacks.event.register(self._deviceEventCallback)

        for callback in self.callbacks.new_device:
            callback(device=device)

    # ------------------------------------------------------------------------------------------------------------------
    def _deviceDisconnected_callback(self, device):
        logger.info(
            f'Device disconnected. Name: {device.information.device_name} ({device.information.device_class}/{device.information.device_type})')
        for callback in self.callbacks.device_disconnected:
            callback(device=device)

    # ------------------------------------------------------------------------------------------------------------------
    def _deviceStreamCallback(self, stream, device, *args, **kwargs):
        for callback in self.callbacks.stream:
            callback(stream, device, *args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------
    def _deviceEventCallback(self, message, device, *args, **kwargs):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def _sendSyncMessage(self, device: Device):

        message = TCP_JSON_Message()
        message.type = 'event'
        message.event = 'sync'
        message.data = {
            'time': time.time()
        }
        device.send(message)

    # ------------------------------------------------------------------------------------------------------------------
    def _sendHeartBeatMessage(self):
        message = TCP_JSON_Message()

        message.type = 'event'
        message.event = 'heartbeat'
        message.data = {
            'time': time.time()
        }
        for id, device in self.devices.items():
            device.send(message)
