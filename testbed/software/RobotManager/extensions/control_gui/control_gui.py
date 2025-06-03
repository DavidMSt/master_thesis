from __future__ import annotations

import math
import random
import time

from core.utils.callbacks import callback_definition, CallbackContainer
from core.utils.colors import rgb_to_hex
from core.utils.logging_utils import Logger
from core.utils.websockets.websockets import SyncWebsocketServer
from extensions.control_gui.src.lib.plot.jsplot import JSPlotTimeSeries
from extensions.control_gui.src.lib.plot.plot_widget import PlotWidget
from extensions.control_gui.src.lib.widgets.buttons import Button
from extensions.control_gui.src.lib.objects import GUI_Object_Group, GUI_Object
from extensions.control_gui.src.lib.utilities import check_for_spaces, split_path, strip_id
from extensions.control_gui.src.lib.map.map_widget import MapWidget

# ======================================================================================================================
'''
Message from Frontend looks like:

'type': 'event',
'event': event_name,
'id': id_of_the_object
'data': data_of_the_object
'''

'''
Messages from the Backend look like:

'type': 'update'
'id': id_of_the_object
'data': data_of_the_object


'type': 'init'
'configuration': ...


'type': 'add'
'id': id_of_the_object
'object_type': type_of_the_object
'configuration': data_of_the_object



'type': 'remove'
'id': id_of_the_object
'''


# === CATEGORY =========================================================================================================
class ControlGUI_Category_Headbar:
    ...

    def __init__(self):
        ...

    def getPayload(self):
        payload = {}
        return payload


# ----------------------------------------------------------------------------------------------------------------------
@callback_definition
class ControlGUI_Category_Callbacks:
    update: CallbackContainer
    add: CallbackContainer
    remove: CallbackContainer


# ----------------------------------------------------------------------------------------------------------------------
class ControlGUI_Category:
    id: str
    pages: dict[str, ControlGUI_Page]

    name: str
    icon: str
    headbar: ControlGUI_Category_Headbar

    configuration: dict

    gui: ControlGui | None

    # === INIT =========================================================================================================
    def __init__(self, id: str, icon: str = None, name: str = None, **kwargs):

        if check_for_spaces(id):
            raise ValueError(f"Category id '{id}' contains spaces")

        default_config = {
            'color': None,
            'max_pages': 10,
        }

        self.configuration = {**default_config, **kwargs}

        self.id = id
        self.icon = icon

        self.name = name if name is not None else id

        self.pages = {}

        self.gui = None

        self.callbacks = ControlGUI_Category_Callbacks()

        self.headbar = ControlGUI_Category_Headbar()

        self.logger = Logger(f"Category {self.id}", 'DEBUG')

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def uid(self):
        return f"/{self.id}"

    # ------------------------------------------------------------------------------------------------------------------
    def getGUI(self):
        return self.gui

    # ------------------------------------------------------------------------------------------------------------------
    def getObjectByPath(self, path: str):
        """
        Given a relative path (e.g. "page1/button1/subgroup/obj2"),
        split off the first segment as the page‐id, find that page,
        and then hand off the remainder of the path to page.getObjectByPath.
        If the remainder is empty, just return the page itself.
        """
        # Trim any leading/trailing slashes and split once
        first_segment, remainder = split_path(path)

        if not first_segment:
            # Path was empty or just "/", nothing to return
            return None

        # Lookup page by its id (self.pages is keyed by page.id)
        if first_segment not in self.pages:
            return None

        page = self.pages[first_segment]
        if not remainder:
            # No more sub‐path: return the page object itself
            return page

        # Otherwise, delegate to the page's getObjectByPath
        return page.getObjectByPath(remainder)

    # ------------------------------------------------------------------------------------------------------------------
    def addPage(self, page: ControlGUI_Page, position=None):

        # Fist check if the position is valid if given
        if position is not None and position > self.configuration['max_pages']:
            raise ValueError(f"Position {position} is out of range")

        if page.id in self.pages:
            raise ValueError(f"Page with id {page.id} already exists")
        self.pages[page.id] = page
        page.category = self
        page.position = position

        # TODO: Send an add message, maybe via callback

    # ------------------------------------------------------------------------------------------------------------------
    def removePage(self, page: ControlGUI_Page):
        if page.id not in self.pages:
            raise ValueError(f"Page with id {page.id} does not exist")
        del self.pages[page.id]

        # TODO: Send remove message. Maybe via callback

    # ------------------------------------------------------------------------------------------------------------------
    def getConfiguration(self) -> dict:
        configuration = {
            'id': self.uid,
            'type': 'category',
            'name': self.name,
            'icon': self.icon,
            'color': rgb_to_hex(self.configuration['color']),
        }
        return configuration

    # ------------------------------------------------------------------------------------------------------------------
    def getPayload(self) -> dict:
        payload = {
            'id': self.uid,
            'type': 'category',
            'config': self.getConfiguration(),
            'headbar': self.headbar.getPayload(),
            'pages': {k: v.getPayload() for k, v in self.pages.items()}
        }
        return payload

    # ------------------------------------------------------------------------------------------------------------------
    def onMessage(self, message):
        self.logger.debug(f"Received message: {message}")
        object_path = message['id']


# === PAGE =============================================================================================================
@callback_definition
class ControlGUI_Page_Callbacks:
    update: CallbackContainer
    add: CallbackContainer
    remove: CallbackContainer


# ----------------------------------------------------------------------------------------------------------------------
class ControlGUI_Page:
    """
    Represents a page in the Control GUI that holds GUI_Object instances
    in a fixed grid layout. Tracks occupied cells and supports manual
    or automatic placement of objects.
    """
    id: str
    objects: dict[str, dict]
    category: ControlGUI_Category | None
    config: dict

    name: str
    icon: str
    position: int | None = None

    def __init__(self, id: str,
                 icon: str = None,
                 name: str = None,
                 **kwargs):
        if check_for_spaces(id):
            raise ValueError(f"Page id '{id}' contains spaces")

        default_config = {
            'color': None,
            'pageColor': [60, 60, 60, 1],
            'grid_size': (18, 50),  # (rows, columns)
        }

        self.config = {**default_config, **kwargs}

        self.id = id
        self.icon = icon
        self.name = name if name is not None else id

        # Grid dimensions
        self._rows, self._cols = self.config['grid_size']
        # Occupancy grid: False = free, True = occupied
        self._occupied = [[False for _ in range(self._cols)] for _ in range(self._rows)]

        self.objects = {}
        self.category = None
        self.callbacks = ControlGUI_Page_Callbacks()
        self.logger = Logger(f"Page {self.id}", 'DEBUG')

    @property
    def uid(self):
        category_id = self.category.uid if self.category is not None else ''
        return f"{category_id}/{self.id}"

    # ------------------------------------------------------------------------------------------------------------------
    def getObjectByPath(self, path: str):
        """
        Given a relative path inside this page (e.g. "button1" or "group1/subobj2"),
        find the direct child whose .id == first segment, then either return it (if
        no remainder) or recurse into it if it's a GUI_Object_Group.
        """
        # Trim any leading/trailing slashes and split into first‐and‐remainder
        first_segment, remainder = split_path(path)

        if not first_segment:
            # Path was empty or just "/", nothing to return
            return None

        # We stored each object in `self.objects` under its full UID, but we want
        # to match on `object.id`. So iterate over self.objects:
        for full_uid, info in self.objects.items():
            obj = info['object']
            if obj.id == first_segment:
                # Found a direct child with matching id
                if not remainder:
                    return obj

                # the remainder exists → must be a group to go deeper
                if isinstance(obj, GUI_Object_Group):
                    return obj.getObjectByPath(remainder)
                else:
                    # Cannot descend further if it's not a group
                    return None

        # If we exit the loop, no matching id was found on this page
        return None

    # ------------------------------------------------------------------------------------------------------------------
    def addObject(self, obj: GUI_Object, row=None, column=None, width=2, height=2):
        """
        Adds an object to the page at a given grid position.
        If the row or column is None, we automatically find the first available
        position for the object's size.
        """
        if obj.uid in self.objects:
            raise ValueError(f"Object with id {obj.uid} already exists on page {self.id}")

        # Determine placement
        if row is None or column is None:
            row, column = self._placeObject(row, column, width, height)
        else:
            self._checkSpace(row, column, width, height)

        # Mark cells occupied
        self._markSpace(row, column, width, height)

        # Store object placement
        self.objects[obj.uid] = {
            'object': obj,
            'row': row,
            'column': column,
            'width': width,
            'height': height,
        }
        obj.parent = self

        self.logger.debug(
            f"Added object {obj.uid} to page {self.id} at ({row}, {column}) with size ({width}, {height})")

    # ------------------------------------------------------------------------------------------------------------------
    def getGUI(self):
        return self.category.getGUI()

    # ------------------------------------------------------------------------------------------------------------------
    def _checkSpace(self, row, column, width, height):
        # Validate bounds
        if row < 1 or column < 1 or row + height - 1 > self._rows or column + width - 1 > self._cols:
            raise ValueError("Object does not fit within grid bounds")
        # Check occupancy
        for r in range(row - 1, row - 1 + height):
            for c in range(column - 1, column - 1 + width):
                if self._occupied[r][c]:
                    raise ValueError("Grid cells already occupied")

    # ------------------------------------------------------------------------------------------------------------------
    def _markSpace(self, row, column, width, height):
        # Mark the grid cells as occupied
        for r in range(row - 1, row - 1 + height):
            for c in range(column - 1, column - 1 + width):
                self._occupied[r][c] = True

    # ------------------------------------------------------------------------------------------------------------------
    def _placeObject(self, row, column, width, height):
        """
        Finds the first available position for an object of given size.
        If one coordinate is fixed, searches along the other.
        """

        # Helper to test a candidate position
        def fits(r, c):
            if r < 1 or c < 1 or r + height - 1 > self._rows or c + width - 1 > self._cols:
                return False
            for rr in range(r - 1, r - 1 + height):
                for cc in range(c - 1, c - 1 + width):
                    if self._occupied[rr][cc]:
                        return False
            return True

        # Neither fixed: scan rows then cols
        if row is None and column is None:
            for r in range(1, self._rows - height + 2):
                for c in range(1, self._cols - width + 2):
                    if fits(r, c):
                        return r, c
        # Row fixed: scan columns
        elif row is not None and column is None:
            for c in range(1, self._cols - width + 2):
                if fits(row, c):
                    return row, c
        # Column fixed: scan rows
        elif column is not None and row is None:
            for r in range(1, self._rows - height + 2):
                if fits(r, column):
                    return r, column

        raise ValueError("No available space to place object")

    # ------------------------------------------------------------------------------------------------------------------
    def getConfiguration(self) -> dict:
        return {
            'id': self.uid,
            'name': self.name,
            'icon': self.icon,
            # 'color': rgb_to_hex(self.config.get('color', [1, 1, 1, 1])),
        }

    # ------------------------------------------------------------------------------------------------------------------
    def getPayload(self) -> dict:
        # Build payload for each object
        objs = {}
        for uid, info in self.objects.items():
            obj = info['object']
            payload = obj.getPayload()
            payload.update({
                'row': info['row'],
                'column': info['column'],
                'width': info['width'],
                'height': info['height'],
            })
            objs[uid] = payload

        return {
            'id': self.uid,
            'type': 'page',
            'position': self.position,
            'config': self.getConfiguration(),
            'objects': objs
        }

    # ------------------------------------------------------------------------------------------------------------------
    def onMessage(self, message):
        self.logger.debug(f"Received message: {message}")


# === GUI ==============================================================================================================
class ControlGui:
    server: SyncWebsocketServer

    categories: dict[str, ControlGUI_Category]

    def __init__(self, host, port=8099, options=None):
        if options is None:
            options = {}

        default_options = {
            'color': [31 / 255, 32 / 255, 35 / 255, 1],
            'rows': 18,
            'columns': 50,
            'max_pages': 10,
            'logo_path': '',
            'name': 'Control GUI',
        }

        self.options = {**default_options, **options}

        self.categories = {}

        self.server = SyncWebsocketServer(host=host, port=port)
        self.server.callbacks.new_client.register(self._new_client_callback)
        self.server.callbacks.client_disconnected.register(self._client_disconnected_callback)
        self.server.callbacks.message.register(self._message_callback)

        self.logger = Logger('GUI', 'DEBUG')

        self.server.start()

    # === METHODS ======================================================================================================
    def addCategory(self, category: ControlGUI_Category):
        if category.id in self.categories:
            raise ValueError(f"Category with id {category.id} already exists")
        self.categories[category.uid] = category
        category.gui = self

        # TODO: Send an add message

    # ------------------------------------------------------------------------------------------------------------------
    def removeCategory(self, category: ControlGUI_Category):
        if category.id not in self.categories:
            raise ValueError(f"Category with id {category.id} does not exist")
        del self.categories[category.uid]

        # TODO: Send a remove message

    # ------------------------------------------------------------------------------------------------------------------
    def broadcast(self, message):
        self.server.send(message)

    # === PRIVATE METHODS ==============================================================================================

    # ------------------------------------------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------------------
    def getElementByUID(self, uid: str):
        """
        Given a full UID (e.g. "/category1/page1/button1" or "/category2/page3"),
        strip the leading slash, split off the first segment (category_id),
        look up that Category in self.categories (keyed by "/<category_id>"),
        and then delegate the remainder to category.getObjectByPath.
        If there is no remainder (just "/category1"), return the category.
        """
        if not uid:
            return None

        # Remove any leading/trailing slashes
        trimmed = uid.strip('/')
        # Split into first (category_id) and remainder
        category_id, remainder = split_path(trimmed)

        if not category_id:
            return None

        # Categories are stored with key == category.uid (which is "/<id>")
        category_key = f"/{category_id}"
        if category_key not in self.categories:
            return None

        category = self.categories[category_key]
        if not remainder:
            # No further path: return the category itself
            return category

        # Delegate to the category's getObjectByPath
        return category.getObjectByPath(remainder)

    # ------------------------------------------------------------------------------------------------------------------
    def getPayload(self):
        payload = {
            'type': 'gui',
            'options': self.options,
            'categories': {k: v.getPayload() for k, v in self.categories.items()}
        }
        return payload

    # ------------------------------------------------------------------------------------------------------------------
    def _initializeClient(self):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def _new_client_callback(self, client):
        self.logger.debug(f"New client connected: {client}")

        # Send Initialize Message
        message = {
            'type': 'init',
            'configuration': self.getPayload(),
        }
        self.server.sendToClient(client, message)

    # ------------------------------------------------------------------------------------------------------------------
    def _client_disconnected_callback(self, client):
        self.logger.debug(f"Client disconnected: {client}")

    # ------------------------------------------------------------------------------------------------------------------
    def _message_callback(self, client, message, *args, **kwargs):
        self.logger.debug(f"Message received: {message}")

        match message['type']:
            case 'event':
                self._handleEventMessage(message)
            case _:
                self.logger.debug(f"Unknown message type: {message['type']}")

    # ------------------------------------------------------------------------------------------------------------------
    def _handleEventMessage(self, message):

        # Check if the message has an ID
        if not message.get('id'):
            self.logger.warning(f"Event message received without id: {message}")
            return

        # Try to find the element with the given ID
        element = self.getElementByUID(message['id'])
        if element is None:
            self.logger.warning(f"Event message received for nonexistent element {message['id']}: {message}")

        element.onMessage(message['data'])


# ======================================================================================================================
def main():
    app = ControlGui('localhost', port=8100)

    category1 = ControlGUI_Category(id='category1',
                                    name='Category 1',
                                    )

    page1 = ControlGUI_Page(id='page1',
                            name='Page 1.1',
                            )

    button1 = Button(id='button1', text='B1', config={})
    button2 = Button(id='button2', text='B2', config={'color': [0.8, 0.1, 0.1]})
    page1.addObject(button1, row=1, column=30, width=5)
    page1.addObject(button2, row=10, column=30, width=2)

    map1 = MapWidget(id='map1')

    p1 = map1.map.add_point(id='point1', x=1, y=2, size=5, color=(1, 0, 0))
    v1 = map1.map.add_vision_agent(id='v1', x=2, y=1, psi=math.radians(-90), size=5, color=(0, 0, 1), )
    map1.map.add_line(id='line1',
                      start=p1,
                      end=v1,
                      color=(0.5, 0.5, 0.5),
                      width=2,
                      mode='object',
                      zindex=5,
                      style='dashed')

    gr1 = map1.map.add_group(group='gr1')

    p2 = gr1.add_point(id='point2', x=-1, y=2, size=5, color=(0.4, 0, 0.4))

    page1.addObject(map1, row=1, column=1, width=20, height=16)

    page2 = ControlGUI_Page(id='page2',
                            name='Page 1.2',
                            color=[0.8, 0.1, 0.1])

    # button3 = Button(id='button3', text='B3', config={})
    # button4 = Button(id='button4', text='B4', config={'color': [0.1, 0.8, 0.1]})
    plot_widget_1 = PlotWidget(id='plot_widget_1')
    timeseries1 = JSPlotTimeSeries(
        id='test',
        name='test',
        precision=2,
        unit='m',
        min=-40,
        max=40,
        color=[0.7, 0, 0.2],
        fill=False,
        width=3,
        tension=0,
        visible=True
    )
    plot_widget_1.plot.addTimeseries(timeseries1)

    page2.addObject(plot_widget_1, row=1, column=1, width=12, height=9)

    plot_widget_2 = PlotWidget(id='plot_widget_2',
                               config={'port': 8005},
                               plot_config={
                                   'show_legend': True,
                               })
    timeseries2 = JSPlotTimeSeries(
        id='test2',
        name='test2',
        precision=2,
        unit='m',
        min=-20,
        max=20,
        color=[0, 0.7, 0.2],
        fill=False,
        width=3,
    )
    plot_widget_2.plot.addTimeseries(timeseries2)
    page2.addObject(plot_widget_2, row=10, column=1, width=12, height=9)

    plot_widget_3 = PlotWidget(id='plot_widget_3', config={'port': 8006})
    timeseries3 = JSPlotTimeSeries(
        id='test3',
        name='test3',
        precision=2,
        unit='m',
        min=-20,
        max=20,
        color=[0, 0.2, 0.7],
        fill=False,
        width=3,
    )
    plot_widget_3.plot.addTimeseries(timeseries3)
    page2.addObject(plot_widget_3, row=1, width=12, height=6)

    plot_widget_4 = PlotWidget(id='plot_widget_4', title='Theta', config={'port': 8007})
    timeseries4 = JSPlotTimeSeries(
        id='test4',
        name='Theta',
        precision=2,
        unit='m',
        min=-20,
        max=20,
        color=[0.5, 0.0, 0.5],
        fill=False,
        width=3,
    )
    plot_widget_4.plot.addTimeseries(timeseries4)
    page2.addObject(plot_widget_4, row=7, width=12, height=6)

    plot_widget_5 = PlotWidget(id='plot_widget_5', title='Psi', config={'port': 8008})
    timeseries5 = JSPlotTimeSeries(
        id='test5',
        name='Theta',
        precision=2,
        unit='m',
        min=-20,
        max=20,
        color=[0.0, 0.5, 0.5],
        fill=False,
        width=3,
    )
    plot_widget_5.plot.addTimeseries(timeseries5)
    page2.addObject(plot_widget_5, row=13, width=12, height=6)

    page3 = ControlGUI_Page(id='page3', name='⚙️ Settings')

    category1.addPage(page2)
    category1.addPage(page1)
    category1.addPage(page3, 10)
    app.addCategory(category1)

    category2 = ControlGUI_Category(id='category2',
                                    name='Category 2',
                                    )

    page3 = ControlGUI_Page(id='page3',
                            name='Page 2.1',
                            color=[0.1, 0.1, 0.8])

    page4 = ControlGUI_Page(id='page4',
                            name='Page 2.2',
                            color=[0.8, 0.8, 0.1])

    category2.addPage(page3)
    category2.addPage(page4)
    app.addCategory(category2)

    while True:
        p1.x += 0.01
        timeseries1.setValue(math.sin(7 * p1.x) * 10 + random.random() * 0)
        timeseries2.setValue(math.cos(7 * p1.x) * 10 + random.random() * 0)
        timeseries3.setValue(math.sin(1 * p1.x) * 4 + random.random() * 0)
        timeseries4.setValue(math.sin(14 * p1.x) * 6 + random.random() * 4)
        time.sleep(0.05)


if __name__ == '__main__':
    main()
