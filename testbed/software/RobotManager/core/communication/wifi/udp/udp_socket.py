import queue
import socket
import threading
import time
from cobs import cobs

from core.utils.callbacks import callback_definition, CallbackContainer
from core.utils.logging_utils import Logger

logger = Logger('UDP Socket')
logger.setLevel('INFO')


@callback_definition
class UDPSocketCallbacks:
    rx: CallbackContainer


########################################################################################################################
class UDP_Socket:
    _socket: socket.socket
    address: str
    port: int
    callbacks: UDPSocketCallbacks
    _thread: threading.Thread

    config: dict
    _exit: bool

    _filterBroadcastEcho: bool
    _rx_queue: queue.Queue
    _thread_timeout = 0.001

    # === INIT =========================================================================================================
    def __init__(self, address, port, config: dict = None):

        self.address = address

        if self.address is None:
            raise Exception('No Local IP address')

        self.port = port
        # self.port = 37022

        if config is None:
            config = {}

        default_config = {
            'cobs': False,
            'filterBroadcastEcho': False,
        }

        self.config = {**default_config, **config}

        self.callbacks = UDPSocketCallbacks()

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._socket.settimeout(0)

        # set ip and port
        self._socket.bind((str(self.address), self.port))
        # self._socket.bind(("", self.port))  # FOR RASPBERRY PI
        self._thread = threading.Thread(target=self._thread_fun)
        self._exit = False

    # === METHODS ======================================================================================================
    def start(self):
        logger.info(
            f"Starting UDP socket on {self.address}:{self.port} (Filter Broadcast Echo={self.config['filterBroadcastEcho']})")
        self._thread.start()

    # ------------------------------------------------------------------------------------------------------------------
    def send(self, data, address: str = '<broadcast>'):

        if isinstance(data, list):
            data = bytes(data)
        if isinstance(data, str):
            data = data.encode('utf-8')

        if self.config['cobs']:
            data = cobs.encode(data)
            data = data + b'\x00'

        try:
            self._socket.sendto(data, (address, self.port))
        except OSError as e:
            logger.error(f"Cannot send data to UDP socket: {e}")

    # ------------------------------------------------------------------------------------------------------------------
    def close(self):
        """

        :return:
        """
        self._exit = True

        if hasattr(self, '_thread') and self._thread.is_alive():
            self._thread.join()

    # ------------------------------------------------------------------------------------------------------------------
    def _thread_fun(self):
        while not self._exit:

            try:
                data, address = self._socket.recvfrom(1028)
                if len(data) > 0:
                    if address[0] == self.address and self.config['filterBroadcastEcho']:
                        ...
                    else:
                        for callback in self.callbacks.rx:
                            callback(data, address, self.port)

            except BlockingIOError:
                pass

            time.sleep(self._thread_timeout)

        logger.info(f"Closing UDP Server on {self.address}: {self.port}")
