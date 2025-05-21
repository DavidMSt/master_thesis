import time
import logging
from websocket_server import WebsocketServer
import websocket
import threading
import json

from core.utils.events import event_definition, ConditionEvent
from core.utils.exit import register_exit_callback
from core.utils.callbacks import CallbackContainer, callback_definition


@callback_definition
class SyncWebsocketServer_Callbacks:
    new_client: CallbackContainer
    client_disconnected: CallbackContainer
    message: CallbackContainer


@event_definition
class SyncWebsocketServer_Events:
    new_client: ConditionEvent
    message: ConditionEvent
    client_disconnected: ConditionEvent


class SyncWebsocketServer:
    callbacks: SyncWebsocketServer_Callbacks
    events: SyncWebsocketServer_Events

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server = WebsocketServer(host=self.host, port=self.port)
        self.clients = []  # Store the connected clients
        self.running = False
        self.thread = None

        self.events = SyncWebsocketServer_Events()
        self.callbacks = SyncWebsocketServer_Callbacks()

        # Exit handling
        register_exit_callback(self.stop)

    def start(self):
        """
        Start the WebSocket server in a separate thread (non-blocking).
        """
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_server, daemon=True)
            self.thread.start()

    def _run_server(self):
        """
        Run the WebSocket server (blocking call). Should be run in a separate thread.
        """
        # Attach callbacks
        self.server.set_fn_new_client(self._on_new_client)
        self.server.set_fn_client_left(self._on_client_left)
        self.server.set_fn_message_received(self._on_message_received)

        try:
            self.server.run_forever()
        except Exception as e:
            ...
            # print(f"Error in server loop: {e}")
        finally:
            self.running = False

    def _on_new_client(self, client, server):
        self.clients.append(client)  # Add client to the list

        self.callbacks.new_client.call(client)
        self.events.new_client.set(client)

    def _on_client_left(self, client, server):
        if client in self.clients:
            self.clients.remove(client)  # Remove client from the list
            self.callbacks.client_disconnected.call(client)
            self.events.client_disconnected.set(client)

    def _on_message_received(self, client, server, message):
        message = json.loads(message)
        self.callbacks.message.call(client, message)
        self.events.message.set(client, message)

    def send(self, message):
        """
        Send a message to all connected clients.
        """
        if isinstance(message, dict):
            message = json.dumps(message)
        for client in self.clients:
            self.server.send_message(client, message)

    def sendToClient(self, client, message):
        """
        Send a message to a specific client.
        """
        if isinstance(message, dict):
            message = json.dumps(message)
        if client in self.clients:
            self.server.send_message(client, message)

    def stop(self, *args, **kwargs):
        """
        Stop the WebSocket server.
        """
        if self.running:
            self.server.shutdown()
            if self.thread:
                self.thread.join()
            self.running = False


# ======================================================================================================================
@callback_definition
class SyncWebsocketClient_Callbacks:
    message: CallbackContainer
    connected: CallbackContainer
    disconnected: CallbackContainer
    error: CallbackContainer


@event_definition
class SyncWebsocketClient_Events:
    message: ConditionEvent
    connected: ConditionEvent
    disconnected: ConditionEvent
    error: ConditionEvent


class SyncWebsocketClient:
    callbacks: SyncWebsocketClient_Callbacks
    events: SyncWebsocketClient_Events

    _thread: threading.Thread
    ws_thread: (None, threading.Thread)
    _exit: bool

    _debug: bool

    def __init__(self, address, port, debug=True):
        self.uri = f"ws://{address}:{port}"
        self.ws = None
        self.connected = False
        self.thread = None
        self.retries = 1000
        self._debug = debug

        self.callbacks = SyncWebsocketClient_Callbacks()
        self.events = SyncWebsocketClient_Events()

        self._thread = threading.Thread(target=self.task, daemon=True)
        self.ws_thread = None
        self._exit = False

        # Disable the internal websocket logger, since it messes with other modules
        logging.getLogger("websocket").setLevel(logging.CRITICAL)

        register_exit_callback(self.close)

    def start(self):
        self._thread.start()

    def close(self, *args, **kwargs):
        print("Close Websocket Client")
        self.ws.close()
        self._exit = True
        self._thread.join()

    def task(self):
        while not self._exit:
            if not self.connected:
                self.connect()
            time.sleep(1)

    def connect(self, retries=None):
        """
        Attempt to connect to the WebSocket server with retry logic.
        """
        retries = retries or self.retries  # Use default or specified retries
        attempt = 0

        while attempt < retries and not self._exit:
            try:
                if self._debug:
                    print(f"Attempting to connect to {self.uri} (Attempt {attempt + 1}/{retries})")

                # Create WebSocket app
                self.ws = websocket.WebSocketApp(self.uri,
                                                 on_open=self.on_open,
                                                 on_close=self.on_close,
                                                 on_message=self.on_message,
                                                 on_error=self.on_error)

                # Run in a separate thread
                self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
                self.ws_thread.start()

                # Wait for connection success or failure
                timeout = 5  # Adjust timeout as needed
                start_time = time.time()

                while not self.connected and time.time() - start_time < timeout:
                    time.sleep(0.1)

                if self.connected:
                    if self._debug:
                        print("Connected successfully!")
                    return  # Exit loop if connection succeeds

                else:  # Timeout
                    self.ws.close()
                    self.ws_thread.join()

            except Exception as e:
                if self._debug:
                    print(f"Connection attempt {attempt + 1} failed: {e}")

            attempt += 1
            time.sleep(1)

        print("Failed to connect after multiple attempts.")

    def send(self, message):
        """
        Send a message to the server.
        """
        if self.connected:
            if isinstance(message, dict):
                message = json.dumps(message)
            self.ws.send(message)

    def disconnect(self):
        """
        Close the WebSocket connection.
        """
        if self.connected:
            self.ws.close()
            self.thread.join()

    def on_open(self, ws):
        self.connected = True
        self.callbacks.connected.call()
        self.events.connected.set()

    def on_close(self, ws, close_status_code, close_msg):
        if self.connected:
            self.connected = False
            self.callbacks.disconnected.call()
            self.events.disconnected.set()

    def on_message(self, ws, message):
        message = json.loads(message)
        self.callbacks.message.call(message)
        self.events.message.set(message)

    def on_error(self, ws, error):
        self.callbacks.error.call(error)
        self.events.error.set(error)
