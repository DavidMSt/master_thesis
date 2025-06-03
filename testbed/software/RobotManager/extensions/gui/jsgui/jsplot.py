import math
import threading
import time

from core.utils.exit import register_exit_callback
from core.utils.logging_utils import Logger
from core.utils.websockets.websockets import SyncWebsocketServer


# ======================================================================================================================
class JSPlotTimeSeries:
    id: str
    name: str
    unit: str
    min: float
    max: float
    precision: int
    fill: bool
    fill_color: list
    width: int

    tension: float

    dimension: int
    value: float

    color: list

    visible: bool

    def __init__(self,
                 id: str,
                 name: str = None,
                 dimension: int = 1,
                 precision: int = 2,
                 unit: str = None,
                 min: float = None,
                 max: float = None,
                 color: list = None,
                 fill: bool = False,
                 fill_color: list = None,
                 width: int = 1,
                 visible: bool = True,
                 y_axis_side: str = 'left',
                 y_axis_grid: bool = True,
                 y_axis_label: str = None,
                 tension: float = 0):

        self.id = id
        self.name = name if name is not None else id
        self.unit = unit
        self.min = min
        self.max = max
        self.dimension = dimension
        self.visible = visible
        self.precision = precision
        self.y_axis_side = y_axis_side
        self.y_axis_grid = y_axis_grid
        self.y_axis_label = y_axis_label
        self.tension = tension

        if dimension != 1:
            raise NotImplementedError("Dimension != 1 not yet implemented")

        self.value = 0

        if color is None:
            color = [0, 0, 0]

        self.color = color

        self.fill = fill

        if fill_color is None:
            fill_color = [0, 0, 0, 0.1]

        self.fill_color = fill_color
        self.width = width

    # ------------------------------------------------------------------------------------------------------------------
    def setValue(self, value: float):
        self.value = value

    # ------------------------------------------------------------------------------------------------------------------
    def getConfig(self):
        return {
            'id': self.id,
            'name': self.name,
            'unit': self.unit,
            'min': self.min,
            'max': self.max,
            'dimension': self.dimension,
            'color': self.color,
            'visible': self.visible,
            'precision': self.precision,
            'fill': self.fill,
            'fill_color': self.fill_color,
            'width': self.width,
            'y_axis_side': self.y_axis_side,
            'y_axis_grid': self.y_axis_grid,
            'y_axis_label': self.y_axis_label,
            'tension': self.tension
        }

    # ------------------------------------------------------------------------------------------------------------------
    def getData(self):
        return {
            'id': self.id,
            'value': self.value,
        }


# ======================================================================================================================
class JSPlot:
    timeseries: dict[str, JSPlotTimeSeries]
    websocket_server: SyncWebsocketServer

    options: dict

    Ts: float
    _thread: threading.Thread
    _exit: bool

    def __init__(self, name: str, host: str = 'localhost', port: int = 8092, Ts=0.02, options: dict = None):

        default_options = {
            'window_time': 10,  # s
            'pre_delay': 0.1,  # s
            'update_time': 0.1,  # s
            'background_color': [1, 1, 1, 1],  # rgba
            'time_ticks_color': [0.5, 0.5, 0.5],  # rgba
            'time_display_format': 'HH:mm:ss',


        }

        self.logger = Logger(f"Plot {name}", 'DEBUG')

        self.options = {**default_options, **(options or {})}

        self.Ts = Ts
        self.server = SyncWebsocketServer(host=host, port=port)
        self.server.callbacks.new_client.register(self._on_new_client)
        self.server.callbacks.client_disconnected.register(self._on_client_disconnected)

        self.timeseries = {}

        self._thread = threading.Thread(target=self._task)

        self._exit = False

        self.server.start()

        self._thread.start()

        register_exit_callback(self.close)

    # ------------------------------------------------------------------------------------------------------------------
    def addTimeseries(self, timeseries: JSPlotTimeSeries):
        if timeseries.id in self.timeseries:
            raise ValueError(f"Timeseries with id {timeseries.id} already exists")

        self.timeseries[timeseries.id] = timeseries

        message = {
            'type': 'add',
            'data': timeseries.getConfig(),
        }

        self.server.send(message)

    # ------------------------------------------------------------------------------------------------------------------
    def removeTimeseries(self, timeseries: JSPlotTimeSeries):
        if timeseries.id in self.timeseries:
            del self.timeseries[timeseries.id]

        message = {
            'type': 'remove',
            'data': timeseries.id,
        }

        self.server.send(message)

    # ------------------------------------------------------------------------------------------------------------------
    def getData(self):
        data = {k: v.getData() for k, v in self.timeseries.items()}
        return data

    # ------------------------------------------------------------------------------------------------------------------
    def getTimeseriesConfig(self):
        return {k: v.getConfig() for k, v in self.timeseries.items()}

    # ------------------------------------------------------------------------------------------------------------------
    def clear(self):
        message = {
            'type': 'clear',
        }
        self.server.send(message)

    # ------------------------------------------------------------------------------------------------------------------
    def close(self):

        message = {
            'type': 'close',
        }
        self.server.send(message)
        time.sleep(0.1)

        self.server.stop()

        if self._thread is not None and self._thread.is_alive():
            self._exit = True
            self._thread.join()

    # ------------------------------------------------------------------------------------------------------------------
    def _task(self):
        while not self._exit:
            message = {
                'type': 'update',
                'time': time.time(),
                'data': self.getData(),
            }
            self.server.send(message)
            time.sleep(self.Ts)

    # ------------------------------------------------------------------------------------------------------------------
    def _on_new_client(self, client):

        self.logger.debug(f"New client connected: {client}")

        message = {
            'type': 'init',
            'options': self.options,
            'timeseries': self.getTimeseriesConfig(),
        }

        self.server.sendToClient(client, message)

    # ------------------------------------------------------------------------------------------------------------------
    def _on_client_disconnected(self, client):
        self.logger.debug(f"Client disconnected: {client}")


# ======================================================================================================================
def main():
    plt = JSPlot('test',
                 Ts=0.02,
                 options={'update_time': 0.05,
                          'window_time': 10,
                          'background_color': [0.97, 0.97, 0.97, 1],
                          })

    timeseries = JSPlotTimeSeries(
        id='test',
        name='test',
        precision=2,
        unit='m',
        min=-40,
        max=40,
        color=[1, 0, 0],
        fill=False,
        width=3,
        tension=0,
        visible=True
    )
    plt.addTimeseries(timeseries)

    timeseries2 = JSPlotTimeSeries(
        id='test2',
        name='test2',
        precision=2,
        unit='m',
        min=-10,
        max=10,
        color=[0, 0, 1],
        fill=True,
        width=3,
        y_axis_side='right',
        y_axis_label='test2',
        y_axis_grid=False
    )
    plt.addTimeseries(timeseries2)

    t = 0
    while True:
        t += 0.01
        timeseries.setValue(9 * math.sin(3*t))
        timeseries2.setValue(3 * math.cos(3*t))
        time.sleep(0.01)


# ======================================================================================================================
if __name__ == '__main__':
    main()
