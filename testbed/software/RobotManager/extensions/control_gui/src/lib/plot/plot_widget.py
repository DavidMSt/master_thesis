from typing import Any

from core.utils.logging_utils import Logger
from extensions.control_gui.src.lib.objects import GUI_Object
from extensions.control_gui.src.lib.map.map import Map
from extensions.control_gui.src.lib.plot.jsplot import JSPlot


class PlotWidget(GUI_Object):
    type = 'plot'
    plot: JSPlot

    # === INIT =========================================================================================================
    def __init__(self, id: str, title: str = None, config=None, plot_config=None):
        super().__init__(id)

        default_config = {
            'server_mode': 'standalone',
            'update_mode': 'continuous',
            'host': 'localhost',
            'port': 8092,
            'Ts': 0.05,
        }

        default_plot_config = {
            'window_time': 10,  # s
            'pre_delay': 0.2,  # s
            'update_time': 0.1,  # s
            'background_color': [1, 1, 1, 0.02],  # rgba
            'time_ticks_color': [0.5, 0.5, 0.5, 0.5],  # rgba
            'time_display_format': 'HH:mm:ss',

            'show_title': True,
            'title': title if title is not None else id,

            'show_legend': True,
        }

        self.config = {**default_config, **(config or {})}
        self.plot_config = {**default_plot_config, **(plot_config or {})}
        self.logger = Logger(f"Plot {self.id}", 'DEBUG')

        self.plot = JSPlot(
            name=self.id,
            server_mode=self.config['server_mode'],
            update_mode=self.config['update_mode'],
            host=self.config['host'],
            port=self.config['port'],
            Ts=self.config['Ts'],
            plot_config=self.plot_config,
        )

    # === METHODS ======================================================================================================
    def getConfiguration(self) -> dict:
        config = {
            'type': self.type,
            'id': self.uid,
            'config': self.config,
            'plot_config': {**self.plot.plot_config, **self.plot_config},
        }
        return config

    # ------------------------------------------------------------------------------------------------------------------
    def getData(self) -> dict:
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def onMessage(self, message) -> Any:
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def update(self, *args, **kwargs):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def init(self, *args, **kwargs):
        pass
    # ------------------------------------------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------------------
