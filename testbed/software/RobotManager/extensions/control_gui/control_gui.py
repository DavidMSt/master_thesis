import time

from core.utils.logging_utils import Logger
from core.utils.websockets.websockets import SyncWebsocketServer
from extensions.control_gui.src.lib.objects import GUI_Object_Group


class ControlGui:
    server: SyncWebsocketServer

    root_group: GUI_Object_Group

    def __init__(self, host, port=8099, options=None):

        if options is None:
            options = {}

        default_options = {

        }

        self.server = SyncWebsocketServer(host=host, port=port)
        self.server.callbacks.new_client.register(self._new_client_callback)
        self.server.callbacks.client_disconnected.register(self._client_disconnected_callback)
        self.server.callbacks.message.register(self._message_callback)



        self.logger = Logger('GUI', 'DEBUG')


        self.server.start()

    # === METHODS ======================================================================================================

    # === PRIVATE METHODS ==============================================================================================

    # ------------------------------------------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------------------
    def _initializeClient(self):
        ...
    # ------------------------------------------------------------------------------------------------------------------
    def _new_client_callback(self, client):
        self.logger.debug(f"New client connected: {client}")

    # ------------------------------------------------------------------------------------------------------------------
    def _client_disconnected_callback(self, client):
        self.logger.debug(f"Client disconnected: {client}")

    # ------------------------------------------------------------------------------------------------------------------
    def _message_callback(self, client, message, *args, **kwargs):
        self.logger.debug(f"Message received: {message}")


def main():
    app = ControlGui('localhost', port=8099)


    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()