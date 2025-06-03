from typing import Any

from core.utils.logging_utils import Logger
from extensions.control_gui.src.lib.objects import GUI_Object
from extensions.control_gui.src.lib.map.map import Map


class MapWidget(GUI_Object):
    type = 'map'
    map: Map

    # === INIT =========================================================================================================
    def __init__(self, id: str, config=None, map_config=None):
        super().__init__(id)

        default_map_config = {

        }

        default_config = {
            'host': 'localhost',
            'port': 8001,
        }

        self.config = {**default_config, **(config or {})}
        self.map_config = {**default_map_config, **(map_config or {})}
        self.logger = Logger(f"Map {self.id}", 'DEBUG')

        self.map = Map(host=self.config['host'], port=self.config['port'], options=self.map_config)

    # ------------------------------------------------------------------------------------------------------------------
    def getConfiguration(self) -> dict:
        config = {
            'type': self.type,
            'id': self.uid,
            'map_config': self.map_config,
        }

        return config

    # ------------------------------------------------------------------------------------------------------------------
    def getData(self) -> dict:
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def onMessage(self, message) -> Any:
        self.logger.debug(f"Received message: {message}")

    # ------------------------------------------------------------------------------------------------------------------
    def update(self, *args, **kwargs):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def init(self, *args, **kwargs):
        pass
