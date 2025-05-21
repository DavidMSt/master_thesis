from __future__ import annotations

import abc
import math
import threading
import time
from abc import abstractmethod
from typing import Optional, Union

from core.utils.exit import register_exit_callback
from core.utils.websockets.websockets import SyncWebsocketServer


# ======================================================================================================================
class MapObject(abc.ABC):
    id: str
    name: str
    show_name: bool
    zindex: int = 10
    parent: Group | None

    def __init__(self, id, name='', show_name: bool = True, zindex: int = 10):
        self.id = id

        if name == "" or name is None:
            name = id

        self.name = name
        self.show_name = show_name
        self.zindex = zindex
        self.parent = None

    def calculatePath(self):
        if self.parent is None:
            return "/" + self.id
        else:
            return self.parent.fullPath.rstrip("/") + "/" + self.id

    @property
    def fullPath(self):
        return self.calculatePath()

    @abstractmethod
    def get_payload(self) -> dict:
        ...


# ======================================================================================================================
class Point(MapObject):
    x: float
    y: float
    color: list
    alpha: float
    dim: bool
    size: float
    shape: str
    show_trails: bool

    def __init__(self, id, x, y, name='', show_name: bool = True, show_trails: bool = True, shape: str = 'circle',
                 color=None, alpha: float = 1,
                 dim: bool = False, size: int = 1, zindex: int = 10):
        super().__init__(id, name, show_name, zindex)
        assert (shape in ['circle', 'square'])
        self.x = x
        self.y = y
        self.color = color
        self.alpha = alpha
        self.dim = dim
        self.size = size
        self.shape = shape

        self.show_trails = show_trails

    def get_payload(self) -> dict:
        return {
            'id': self.id,
            'path': self.fullPath,
            'type': 'point',
            'data': {
                'x': self.x,
                'y': self.y,
                'color': self.color,
                'alpha': self.alpha,
                'dim': self.dim,
                'size': self.size,
                'shape': self.shape,
                'zindex': self.zindex,
                'name': self.name,
                'show_name': self.show_name,
                'show_trails': self.show_trails,
            }
        }


# ======================================================================================================================
class Agent(MapObject):
    x: float
    y: float
    psi: float
    color: list
    alpha: float
    dim: bool
    size: float
    shape: str
    text: str
    show_trails: bool

    def __init__(self, id, x, y, psi, name='', show_name: bool = True, show_trails: bool = True, color=None,
                 alpha: float = 1, dim: bool = False,
                 size: int = 1,
                 shape: str = "circle",
                 text: str = "",
                 zindex: int = 10):
        super().__init__(id, name, show_name, zindex)
        self.x = x
        self.y = y
        self.psi = psi
        self.color = color
        self.alpha = alpha
        self.dim = dim
        self.size = size
        self.shape = shape
        self.text = text

        self.show_trails = show_trails

    def get_payload(self) -> dict:
        return {
            'id': self.id,
            'path': self.fullPath,
            'type': 'agent',
            'data': {
                'x': self.x,
                'y': self.y,
                'psi': self.psi,
                'color': self.color,
                'alpha': self.alpha,
                'dim': self.dim,
                'size': self.size,
                'shape': self.shape,
                'text': self.text,
                'zindex': self.zindex,
                'name': self.name,
                'show_name': self.show_name,
                'show_trails': self.show_trails,
            }
        }


# ======================================================================================================================
class VisionAgent(Agent):
    vision_radius: float
    vision_fov: float

    def __init__(self, id, x, y, psi, name='', show_name: bool = True, show_trails: bool = True,
                 vision_radius: float = 1,
                 vision_fov: float = math.radians(120), color=None,
                 alpha: float = 1, dim: bool = False, size: int = 1, shape: str = "circle", text: str = "",
                 zindex: int = 10):
        super().__init__(id, x, y, psi, name, show_name, show_trails, color, alpha, dim, size, shape, text, zindex)
        self.vision_radius = vision_radius
        self.vision_fov = vision_fov

    def get_payload(self) -> dict:
        return {
            'id': self.id,
            'path': self.fullPath,
            'type': 'vision_agent',
            'data': {
                'x': self.x,
                'y': self.y,
                'psi': self.psi,
                'vision_radius': self.vision_radius,
                'vision_fov': self.vision_fov,
                'color': self.color,
                'alpha': self.alpha,
                'dim': self.dim,
                'size': self.size,
                'shape': self.shape,
                'text': self.text,
                'zindex': self.zindex,
                'name': self.name,
                'show_name': self.show_name,
                'show_trails': self.show_trails,
            }
        }


# ======================================================================================================================
class Vector(MapObject):
    origin: list
    vec: list
    color: list
    alpha: float
    dim: bool
    width: float

    def __init__(self, id, origin, vec, name='', show_name: bool = True, color=None, alpha: float = 1,
                 dim: bool = False, width: int = 1, zindex: int = 10):
        super().__init__(id, name, show_name, zindex)
        self.origin = origin
        self.vec = vec
        self.color = color
        self.alpha = alpha
        self.dim = dim
        self.width = width

    def get_payload(self) -> dict:
        return {
            'id': self.id,
            'path': self.fullPath,
            'type': 'vector',
            'data': {
                'origin': self.origin,
                'vec': self.vec,
                'color': self.color,
                'alpha': self.alpha,
                'dim': self.dim,
                'width': self.width,
                'zindex': self.zindex,
                'name': self.name,
                'show_name': self.show_name,
            }
        }


# ======================================================================================================================
class Line(MapObject):
    start: MapObject | list[float]
    end: MapObject | list[float]
    mode: str
    color: list
    alpha: float
    dim: bool
    width: float

    def __init__(self, id, mode: str, start: MapObject | list, end: MapObject | list, name='', show_name: bool = True,
                 color=None, alpha: float = 1,
                 dim: bool = False, width: int = 1, style: str = "solid", zindex: int = 10):
        super().__init__(id, name, show_name, zindex)

        assert style in ['solid', 'dashed', 'dotted']

        assert mode in ['coordinate', 'object']

        self.start = start
        self.end = end
        self.color = color
        self.alpha = alpha
        self.dim = dim
        self.width = width
        self.style = style

    @staticmethod
    def get_coordinates(obj: MapObject) -> list[float]:

        match obj:
            case CoordinateSystem():
                return obj.origin
            case Point():
                return [obj.x, obj.y]
            case Agent():
                return [obj.x, obj.y]
            case VisionAgent():
                return [obj.x, obj.y]
        return [0, 0]

    def get_payload(self) -> dict:
        return {
            'id': self.id,
            'path': self.fullPath,
            'type': 'line',
            'data': {
                'start': self.get_coordinates(self.start) if isinstance(self.start, MapObject) else self.start,
                'end': self.get_coordinates(self.end) if isinstance(self.end, MapObject) else self.end,
                'color': self.color,
                'alpha': self.alpha,
                'dim': self.dim,
                'width': self.width,
                'style': self.style,
                'zindex': self.zindex,
                'name': self.name,
                'show_name': self.show_name,
            }
        }


# ======================================================================================================================
class CoordinateSystem(MapObject):
    origin: list[float]
    x_axis: list[float]
    y_axis: list[float]
    colors: dict[str, list[float]]
    alpha: float
    dim: bool
    width: float
    text: str

    def __init__(self, id, origin, x_axis, y_axis, name='', show_name: bool = True,
                 colors: dict[str, list[float]] = None, alpha: float = 1, dim: bool = False,
                 width: int = 1, text: str = "", zindex: int = 10):
        super().__init__(id, name, show_name, zindex)
        self.origin = origin
        self.x_axis = x_axis
        self.y_axis = y_axis
        self.colors = colors
        self.alpha = alpha
        self.dim = dim
        self.width = width
        self.text = text

    def get_payload(self) -> dict:
        return {
            'id': self.id,
            'path': self.fullPath,
            'type': 'coordinate_system',
            'data': {
                'origin': self.origin,
                'x_axis': self.x_axis,
                'y_axis': self.y_axis,
                'colors': self.colors,
                'alpha': self.alpha,
                'dim': self.dim,
                'width': self.width,
                'text': self.text,
                'zindex': self.zindex,
                'name': self.name,
                'show_name': self.show_name,
            }
        }


# ======================================================================================================================
class Rectangle(MapObject):
    origin: [str, list[float]]
    size: [str, list[float]]
    color: list
    linecolor: list
    alpha: float
    dim: bool

    def __init__(self, id, origin, size, name='', show_name: bool = False, color=None, linecolor=None, alpha: float = 1,
                 dim: bool = False,
                 zindex: int = 10):
        super().__init__(id, name, show_name, zindex)
        self.origin = origin
        self.size = size
        self.color = color
        self.linecolor = linecolor
        self.alpha = alpha
        self.dim = dim

    def get_payload(self) -> dict:
        return {
            'id': self.id,
            'path': self.fullPath,
            'type': 'rectangle',
            'data': {
                'origin': self.origin,
                'size': self.size,
                'color': self.color,
                'linecolor': self.linecolor,
                'alpha': self.alpha,
                'dim': self.dim,
                'zindex': self.zindex,
                'name': self.name,
                'show_name': self.show_name,
            }
        }


# ======================================================================================================================
class Circle(MapObject):
    origin: [str, list[float]]
    diameter: float
    color: list
    linecolor: list
    alpha: float
    dim: bool

    def __init__(self, id, origin, diameter, name='', show_name: bool = False, color=None, linecolor=None,
                 alpha: float = 1, dim: bool = False,
                 zindex: int = 10):
        super().__init__(id, name, show_name, zindex)
        self.origin = origin
        self.diameter = diameter
        self.color = color
        self.linecolor = linecolor
        self.alpha = alpha
        self.dim = dim

    def get_payload(self) -> dict:
        return {
            'id': self.id,
            'path': self.fullPath,
            'type': 'circle',
            'data': {
                'origin': self.origin,
                'diameter': self.diameter,
                'color': self.color,
                'linecolor': self.linecolor,
                'alpha': self.alpha,
                'dim': self.dim,
                'zindex': self.zindex,
                'name': self.name,
                'show_name': self.show_name,
            }
        }


# ======================================================================================================================
class Group:
    id: str
    visible: bool
    parent: Optional[Group]
    groups: dict[str, Group]
    points: dict[str, Point]
    agents: dict[str, Agent]
    vision_agents: dict[str, VisionAgent]
    coordinate_systems: dict[str, CoordinateSystem]
    vectors: dict[str, Vector]
    lines: dict[str, Line]
    rectangles: dict[str, Rectangle]
    circles: dict[str, Circle]

    map: Map | None

    def __init__(self, id, parent=None, visible: bool = True, *args, **kwargs):
        self.id = id
        self.parent = parent
        self.groups = {}
        self.points = {}
        self.agents = {}
        self.vision_agents = {}
        self.coordinate_systems = {}
        self.vectors = {}
        self.lines = {}
        self.rectangles = {}
        self.circles = {}
        self.map = None
        self.visible = visible

    @property
    def fullPath(self) -> str:
        if self.parent is None:
            return "/" + self.id
        else:
            return self.parent.fullPath + "/" + self.id

    # ------------------------------------------------------------------------------------------------------------------
    def get_root(self) -> Group:
        if self.parent is None:
            return self
        else:
            return self.parent.get_root()

    # ------------------------------------------------------------------------------------------------------------------
    def get_map(self):
        return self.get_root().map

    # ------------------------------------------------------------------------------------------------------------------
    def find_absolute_path(self, target) -> Optional[str]:
        for container in [self.points, self.agents, self.vision_agents, self.vectors,
                          self.coordinate_systems, self.lines, self.rectangles, self.circles]:
            for el in container.values():
                if el is target:
                    return target.fullPath
        for sub in self.groups.values():
            path = sub.find_absolute_path(target)
            if path is not None:
                return path
        return None

    # ------------------------------------------------------------------------------------------------------------------
    def get_element_by_id(self, path: str) -> MapObject | Group | None:
        tokens = path.strip("/").split("/")
        if not tokens:
            return None
        current_group = self
        for token in tokens[:-1]:
            current_group = current_group.groups.get(token)
            if current_group is None:
                return None
        last_token = tokens[-1]
        if last_token in current_group.groups:
            return current_group.groups[last_token]
        if last_token in current_group.points:
            return current_group.points[last_token]
        if last_token in current_group.agents:
            return current_group.agents[last_token]
        if last_token in current_group.vision_agents:
            return current_group.vision_agents[last_token]
        if last_token in current_group.vectors:
            return current_group.vectors[last_token]
        if last_token in current_group.coordinate_systems:
            return current_group.coordinate_systems[last_token]
        if last_token in current_group.lines:
            return current_group.lines[last_token]
        if last_token in current_group.rectangles:
            return current_group.rectangles[last_token]
        if last_token in current_group.circles:
            return current_group.circles[last_token]
        return None

    # ------------------------------------------------------------------------------------------------------------------
    def remove_element_by_id(self, path: str) -> Optional[
        Union["Group", Point, Agent, VisionAgent, Vector, CoordinateSystem, Line, Rectangle, Circle]]:
        tokens = path.strip("/").split("/")
        if not tokens:
            return None
        current_group = self
        for token in tokens[:-1]:
            current_group = current_group.groups.get(token)
            if current_group is None:
                return None
        last_token = tokens[-1]
        if last_token in current_group.groups:
            return current_group.groups.pop(last_token)
        if last_token in current_group.points:
            return current_group.points.pop(last_token)
        if last_token in current_group.agents:
            return current_group.agents.pop(last_token)
        if last_token in current_group.vision_agents:
            return current_group.vision_agents.pop(last_token)
        if last_token in current_group.vectors:
            return current_group.vectors.pop(last_token)
        if last_token in current_group.coordinate_systems:
            return current_group.coordinate_systems.pop(last_token)
        if last_token in current_group.lines:
            return current_group.lines.pop(last_token)
        if last_token in current_group.rectangles:
            return current_group.rectangles.pop(last_token)
        if last_token in current_group.circles:
            return current_group.circles.pop(last_token)
        return None

    # ------------------------------------------------------------------------------------------------------------------
    def add_point(self, id, x, y, shape='circle', name='', show_name: bool = True, show_trails: bool = True, color=None,
                  alpha: float = 1, dim: bool = False, size: int = 1, zindex: int = 10):
        if id in self.points:
            raise ValueError(f"Point with id {id} already exists.")
        point = Point(id, x, y, name, show_name, show_trails, shape, color, alpha, dim, size, zindex)
        point.parent = self
        self.points[id] = point

        self._addObject(point)
        return point

    # ------------------------------------------------------------------------------------------------------------------
    # Write the add_agent function
    # ------------------------------------------------------------------------------------------------------------------
    def add_agent(self, id, x, y, psi, name='', show_name: bool = True, show_trails: bool = True,
                  color=None, alpha: float = 1, dim: bool = False, size: int = 1,
                  shape: str = "circle", text: str = "", zindex: int = 10):
        if id in self.agents:
            raise ValueError(f"Agent with id {id} already exists.")
        agent = Agent(id, x, y, psi, name, show_name, show_trails, color, alpha, dim, size, shape, text, zindex)
        agent.parent = self
        self.agents[id] = agent
        self._addObject(agent)
        return agent

    # ------------------------------------------------------------------------------------------------------------------
    def add_vision_agent(self, id, x, y, psi, name='', show_name: bool = True,
                         show_trails: bool = True, vision_radius: float = 1, vision_fov: float = math.radians(120),
                         color=None, alpha: float = 1, dim: bool = False, size: int = 1, shape: str = "circle",
                         text: str = "", zindex: int = 10):
        if id in self.vision_agents:
            raise ValueError(f"Vision agent with id {id} already exists.")
        vision_agent = VisionAgent(id, x, y, psi, name, show_name, show_trails, vision_radius, vision_fov, color, alpha,
                                   dim, size, shape, text, zindex)
        vision_agent.parent = self
        self.vision_agents[id] = vision_agent
        self._addObject(vision_agent)
        return vision_agent

    # ------------------------------------------------------------------------------------------------------------------
    def add_vector(self, id, origin, vec, name='', show_name: bool = True, color=None, alpha: float = 1,
                   dim: bool = False, size: int = 1,
                   zindex: int = 10):
        if id in self.vectors:
            raise ValueError(f"Vector with id {id} already exists.")
        vector = Vector(id, origin, vec, name, show_name, color, alpha, dim, size, zindex)
        vector.parent = self
        self.vectors[id] = vector
        self._addObject(vector)
        return vector

    # ------------------------------------------------------------------------------------------------------------------
    def add_coordinate_system(self, id, origin, x_axis, y_axis, name='', show_name: bool = True,
                              colors: dict[str, list[float]] = None, alpha: float = 1,
                              dim: bool = False, width: int = 1, text: str = "", zindex: int = 10):
        if id in self.coordinate_systems:
            raise ValueError(f"Coordinate system with id {id} already exists.")
        coordinate_system = CoordinateSystem(id, origin, x_axis, y_axis, name, show_name, colors, alpha, dim, width,
                                             text, zindex)
        coordinate_system.parent = self
        self.coordinate_systems[id] = coordinate_system
        self._addObject(coordinate_system)
        return coordinate_system

    # ------------------------------------------------------------------------------------------------------------------
    def add_circle(self, id, origin, diameter, name='', show_name: bool = False, color=None, linecolor=None,
                   alpha: float = 1, dim: bool = False,
                   zindex: int = 10):
        if id in self.circles:
            raise ValueError(f"Circle with id {id} already exists.")
        circle = Circle(id, origin, diameter, name, show_name, color, linecolor, alpha, dim, zindex)
        circle.parent = self
        self.circles[id] = circle
        self._addObject(circle)
        return circle

    # ------------------------------------------------------------------------------------------------------------------
    def add_rectangle(self, id, origin, size, name='', show_name: bool = False, color=None, linecolor=None,
                      alpha: float = 1, dim: bool = False,
                      zindex: int = 10, ):
        if id in self.rectangles:
            raise ValueError(f"Rectangle with id {id} already exists.")
        rectangle = Rectangle(id, origin, size, name, show_name, color, linecolor, alpha, dim, zindex)
        rectangle.parent = self
        self.rectangles[id] = rectangle
        self._addObject(rectangle)
        return rectangle

    # ------------------------------------------------------------------------------------------------------------------
    def add_line(self, id, mode: str, start: str | MapObject | list, end: str | MapObject | list, name='',
                 show_name: bool = True, color=None,
                 alpha: float = 1,
                 dim: bool = False, width: int = 1, style: str = 'solid', zindex: int = 10, ):
        if id in self.lines:
            raise ValueError(f"Line with id {id} already exists.")

        assert (mode in ['coordinate', 'object'])

        if isinstance(start, str):
            start = self.get_element_by_id(start)
        if isinstance(end, str):
            end = self.get_element_by_id(end)

        line = Line(id, mode, start, end, name, show_name, color, alpha, dim, width, style, zindex)
        line.parent = self
        self.lines[id] = line
        self._addObject(line)
        return line

    # ------------------------------------------------------------------------------------------------------------------
    def add_group(self, group: Group | str, *args, **kwargs) -> Group:
        if isinstance(group, str):
            group = Group(group, self, *args, **kwargs)
        if group.id in self.groups:
            raise ValueError(f"Group with id {group.id} already exists.")
        group.parent = self
        self.groups[group.id] = group
        self._addObject(group)
        return group

    # ------------------------------------------------------------------------------------------------------------------
    def get_payload(self) -> dict:

        return {
            'id': self.id,
            'path': self.fullPath,
            'type': 'group',
            'visible': self.visible,
            'data': {
                'groups': {k: v.get_payload() for k, v in self.groups.items()},
                'points': {k: v.get_payload() for k, v in self.points.items()},
                'agents': {k: v.get_payload() for k, v in self.agents.items()},
                'vision_agents': {k: v.get_payload() for k, v in self.vision_agents.items()},
                'vectors': {k: v.get_payload() for k, v in self.vectors.items()},
                'coordinate_systems': {k: v.get_payload() for k, v in self.coordinate_systems.items()},
                'lines': {k: v.get_payload() for k, v in self.lines.items()},
                'rectangles': {k: v.get_payload() for k, v in self.rectangles.items()},
                'circles': {k: v.get_payload() for k, v in self.circles.items()},
            }
        }

    # ------------------------------------------------------------------------------------------------------------------
    def _addObject(self, object: MapObject | Group):
        map = self.get_map()
        if map is not None:
            map.addObject(object)

    # ------------------------------------------------------------------------------------------------------------------
    def _removeObject(self, object: MapObject | Group):
        map = self.get_map()
        if map is not None:
            map.removeObject(object)


# ======================================================================================================================
class Map:
    server: SyncWebsocketServer

    _root: Group
    _thread: threading.Thread
    _exit: bool = False

    options: dict

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 options: dict = None,
                 host='localhost',
                 port=8091):

        default_options = {
            'coordinate_system_size': 1,
            'trails_size': 5,
            'trails_alpha': 0.3,
            'trails_memory_length': 15,  # In seconds. If None, all time is stored
            'size': (10, 10),  # Determines the size of the map in meters. (None, None) makes the grid indefinitely big
            'center': (1, 0),
            'grid': 0.5,
            'initial_display': (12, 12, 0, 0),  # (width, height, zoom x, zoom y)
            'background_color': (1, 1, 1),
            'grid_color': (0.7, 0.7, 0.7),
            'grid_width': 1,  # NEW,
            'major_grid_style': 'solid',  # NEW can be solid or dotted
            'minor_grid_style': 'dotted',  # NEW can be solid or dotted
            'grid_border_width': 3,  # NEW
            'ticks_color': (0, 0, 0)
        }

        self.options = {**default_options, **(options or {})}

        self.server = SyncWebsocketServer(host=host, port=port)

        self.server.callbacks.new_client.register(self._on_new_client)

        self.server.start()
        self._root = Group("root")
        self._root.map = self
        self._thread = threading.Thread(target=self._task, daemon=True)
        self._thread.start()
        register_exit_callback(self.close)

    # ------------------------------------------------------------------------------------------------------------------
    def close(self):
        self.server.send({
            'command': 'stop',
        })
        self.server.stop()
        self._exit = True
        if self._thread is not None and self._thread.is_alive():
            self._thread.join()

    # ------------------------------------------------------------------------------------------------------------------
    def get_root(self) -> Group:
        return self._root

    # ------------------------------------------------------------------------------------------------------------------
    def add_point(self, *args, **kwargs) -> Point:
        return self._root.add_point(*args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------
    def add_agent(self, *args, **kwargs) -> Agent:
        return self._root.add_agent(*args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------
    def add_vision_agent(self, *args, **kwargs) -> VisionAgent:
        return self._root.add_vision_agent(*args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------
    def add_vector(self, *args, **kwargs) -> Vector:
        return self._root.add_vector(*args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------
    def add_coordinate_system(self, *args, **kwargs) -> CoordinateSystem:
        return self._root.add_coordinate_system(*args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------
    def add_circle(self, *args, **kwargs) -> Circle:
        return self._root.add_circle(*args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------
    def add_rectangle(self, *args, **kwargs) -> Rectangle:
        return self._root.add_rectangle(*args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------
    def add_line(self, *args, **kwargs) -> Line:
        return self._root.add_line(*args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------
    def add_group(self, *args, **kwargs) -> Group:
        return self._root.add_group(*args, **kwargs)

    # ------------------------------------------------------------------------------------------------------------------
    def get_element_by_id(self, path: str) -> MapObject | Group:
        return self._root.get_element_by_id(path)

    # ------------------------------------------------------------------------------------------------------------------
    def remove_element_by_id(self, path: str) -> Optional[
        Union["Group", Point, Agent, VisionAgent, Vector, CoordinateSystem, Line, Rectangle, Circle]]:
        return self._root.remove_element_by_id(path)

    # ------------------------------------------------------------------------------------------------------------------
    def get_update_data(self) -> dict:
        return {
            'command': 'update',
            'data': self._root.get_payload(),
        }

    # ------------------------------------------------------------------------------------------------------------------
    def _task(self):
        while not self._exit:
            data: dict = self.get_update_data()
            self.server.send(data)
            time.sleep(0.05)

    # ------------------------------------------------------------------------------------------------------------------
    def _on_new_client(self, client):
        print(f"New client connected: {client}")
        message = {
            'command': 'init',
            'options': self.options,
            'data': self._root.get_payload(),
        }
        self.server.sendToClient(
            client=client,
            message=message)

    # ------------------------------------------------------------------------------------------------------------------
    def addObject(self, object: MapObject):
        message = {
            'command': 'add',
            'data': object.get_payload(),
        }
        self.server.send(message)

    # ------------------------------------------------------------------------------------------------------------------
    def removeObject(self, object: MapObject):
        message = {
            'command': 'remove',
            'data': object.get_payload(),
        }
        self.server.send(message)


def main():
    map = Map(options={
        'size': (12, 12),
        'grid': 0.3
    })
    group1 = map.add_group("group1")

    point1 = group1.add_point("point1", 1, 1, size=5, color=[1, 0, 0])
    agent1 = group1.add_agent("agent1", 2, 2, psi=math.radians(0), size=10, color=[0, 1, 0], name='Steve')
    visionagent1 = group1.add_vision_agent("visionagent1", 3, 3, math.radians(90), size=10, color=[0, 0, 1])
    line1 = group1.add_line("line1", "object", start=point1, end=agent1, color=[0, 0, 0], width=3, zindex=1,
                            style='dashed', alpha=0.9)
    vector1 = group1.add_vector("vector1", [0, 0], [-1, -1], color=[0, 0, 1], size=3)
    rectangle1 = group1.add_rectangle("rectangle1", [0, 0], [3, 3], color=[1, 0, 0], alpha=0.1)
    circle1 = group1.add_circle("circle1", [-1, 3], 1, color=[0, 1, 0], alpha=0.9)
    point3 = group1.add_point("point3", -1, 3, size=5, color=[1, 0, 0], zindex=15)

    group2 = group1.add_group("group2", visible=False)

    group2.add_point("point2", 4, 4, size=5, color=[1, 0, 0], shape='square')
    print(point1)

    while True:
        point1.x += 0.01
        visionagent1.psi += 0.1
        visionagent1.x += 0.01
        time.sleep(0.1)


if __name__ == '__main__':
    main()