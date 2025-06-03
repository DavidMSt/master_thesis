import abc
import math
from abc import abstractmethod
from typing import Any


# ======================================================================================================================
class MapObject(abc.ABC):
    id: str
    name: str
    show_name: bool
    zindex: int = 10
    parent: Any | None

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