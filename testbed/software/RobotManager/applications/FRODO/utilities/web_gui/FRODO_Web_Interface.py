import dataclasses
import os
import threading
import time
import webbrowser

from core.utils.exit import register_exit_callback
from core.utils.websockets.websockets import SyncWebsocketServer

from dataclasses import dataclass, field, fields
from typing import Optional, List, Dict, Union, Any


def asdict_no_parent(obj):
    """
    Recursively convert a dataclass to a dictionary,
    excluding any field named 'parent' to avoid circular references.
    """
    if dataclasses.is_dataclass(obj):
        result = {}
        for f in fields(obj):
            if f.name == "parent":
                continue
            value = getattr(obj, f.name)
            result[f.name] = asdict_no_parent(value)
        return result
    elif isinstance(obj, (list, tuple)):
        return type(obj)(asdict_no_parent(item) for item in obj)
    elif isinstance(obj, dict):
        return type(obj)((key, asdict_no_parent(value)) for key, value in obj.items())
    else:
        return obj


# -----------------------------------------------------------------------------
# Plottable Elements with only the essential properties.
# -----------------------------------------------------------------------------

@dataclass
class PlottableElement:
    id: str = ''
    parent: Optional["Group"] = field(default=None, repr=False, compare=False)

    def calculatePath(self):
        if self.parent is None:
            return "/" + self.id
        else:
            return self.parent.fullPath.rstrip("/") + "/" + self.id

    @property
    def fullPath(self):
        return self.calculatePath()


@dataclass
class Video(PlottableElement):
    title: str = ''
    address: str = ''
    port: int = 0
    placeholder: bool = False


@dataclass
class Point(PlottableElement):
    x: float = 0.0
    y: float = 0.0
    color: Optional[List[float]] = None
    alpha: Optional[float] = 1
    dim: bool = False
    size: float = 1


@dataclass
class Agent(PlottableElement):
    position: List[float] = field(default_factory=list)
    psi: float = 0.0
    color: Optional[List[float]] = None
    text: Optional[str] = None
    alpha: Optional[float] = 1
    size: float = 1
    shape: str = 'circle'


@dataclass
class VisionAgent(Agent):
    vision_radius: float = 0.0
    vision_fov: float = 0.0


@dataclass
class Vector(PlottableElement):
    origin: List[float] = field(default_factory=list)
    vec: List[float] = field(default_factory=list)
    color: Optional[List[float]] = None
    text: Optional[str] = None


@dataclass
class CoordinateSystem(PlottableElement):
    origin: List[float] = field(default_factory=list)
    ex: List[float] = field(default_factory=list)
    ey: List[float] = field(default_factory=list)
    colors: Optional[Dict[str, List[float]]] = None
    text: Optional[str] = None


@dataclass
class Line(PlottableElement):
    start: Union[str, List[float]] = ""
    end: Union[str, List[float]] = ""
    color: Optional[List[float]] = None
    text: Optional[str] = None
    # Hidden references to the start and end elements if provided:
    _start_element: Optional[Any] = field(default=None, init=False, repr=False, compare=False)
    _end_element: Optional[Any] = field(default=None, init=False, repr=False, compare=False)


@dataclass
class Rectangle(PlottableElement):
    mid: List[float] = field(default_factory=list)
    x: float = 0.0
    y: Optional[float] = None
    fill: Optional[List[float]] = None
    linecolor: Optional[List[float]] = None


@dataclass
class Circle(PlottableElement):
    mid: List[float] = field(default_factory=list)
    diameter: float = 0.0
    fill: Optional[List[float]] = None
    linecolor: Optional[List[float]] = None
    alpha: Optional[float] = 1


# -----------------------------------------------------------------------------
# Group Container with add functions, helper methods, and a to_dict method.
# -----------------------------------------------------------------------------

@dataclass
class Group(PlottableElement):
    points: Dict[str, Point] = field(default_factory=dict)
    agents: Dict[str, Agent] = field(default_factory=dict)
    visionagents: Dict[str, VisionAgent] = field(default_factory=dict)
    vectors: Dict[str, Vector] = field(default_factory=dict)
    coordinate_systems: Dict[str, CoordinateSystem] = field(default_factory=dict)
    lines: Dict[str, Line] = field(default_factory=dict)
    rectangles: Dict[str, Rectangle] = field(default_factory=dict)
    circles: Dict[str, Circle] = field(default_factory=dict)
    groups: Dict[str, "Group"] = field(default_factory=dict)
    name: str = ''  # For display purposes.

    def __post_init__(self):
        self.name = self.id

    def get_root(self) -> "Group":
        if self.parent is None:
            return self
        return self.parent.get_root()

    def find_absolute_path(self, target) -> Optional[str]:
        for container in [self.points, self.agents, self.visionagents, self.vectors,
                          self.coordinate_systems, self.lines, self.rectangles, self.circles]:
            for el in container.values():
                if el is target:
                    return target.fullPath
        for sub in self.groups.values():
            path = sub.find_absolute_path(target)
            if path is not None:
                return path
        return None

    def get_element_by_id(self, path: str) -> Optional[
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
            return current_group.groups[last_token]
        if last_token in current_group.points:
            return current_group.points[last_token]
        if last_token in current_group.agents:
            return current_group.agents[last_token]
        if last_token in current_group.visionagents:
            return current_group.visionagents[last_token]
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
        if last_token in current_group.visionagents:
            return current_group.visionagents.pop(last_token)
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

    def add_point(self, id: str, x: float, y: float, **kwargs) -> Point:
        point = Point(id=id, x=x, y=y, **kwargs)
        point.parent = self
        self.points[id] = point
        return point

    def add_agent(self, id: str, position: List[float], psi: float, **kwargs) -> Agent:
        agent = Agent(id=id, position=position, psi=psi, **kwargs)
        agent.parent = self
        self.agents[id] = agent
        return agent

    def add_vision_agent(self, id: str | VisionAgent, position: List[float] = None, psi: float = 0, vision_radius: float = 0,
                         vision_fov: float = 0, **kwargs) -> VisionAgent:
        if isinstance(id, VisionAgent):
            vag = id
            vag.parent = self
            self.visionagents[vag.id] = vag
        else:
            if position is None:
                position = [0, 0]
            vag = VisionAgent(id=id, position=position, psi=psi, vision_radius=vision_radius, vision_fov=vision_fov,
                              **kwargs)
            vag.parent = self
            self.visionagents[id] = vag

        return vag

    def add_vector(self, id: str, origin: List[float], vec: List[float], **kwargs) -> Vector:
        vector = Vector(id=id, origin=origin, vec=vec, **kwargs)
        vector.parent = self
        self.vectors[id] = vector
        return vector

    def add_coordinate_system(self, id: str, origin: List[float], ex: List[float], ey: List[float],
                              **kwargs) -> CoordinateSystem:
        cs = CoordinateSystem(id=id, origin=origin, ex=ex, ey=ey, **kwargs)
        cs.parent = self
        self.coordinate_systems[id] = cs
        return cs

    def add_line(self, id: str, start: Union[str, List[float], object], end: Union[str, List[float], object],
                 **kwargs) -> Line:
        _start = start
        _end = end
        if not isinstance(start, (str, list)):
            _start = start.fullPath
        if not isinstance(end, (str, list)):
            _end = end.fullPath
        line = Line(id=id, start=_start, end=_end, **kwargs)
        line.parent = self
        if not isinstance(start, (str, list)):
            line._start_element = start
        if not isinstance(end, (str, list)):
            line._end_element = end
        self.lines[id] = line
        return line

    def add_rectangle(self, id: str, mid: List[float], x: float, y: Optional[float] = None, **kwargs) -> Rectangle:
        rect = Rectangle(id=id, mid=mid, x=x, y=y, **kwargs)
        rect.parent = self
        self.rectangles[id] = rect
        return rect

    def add_circle(self, id: str | Circle, mid: List[float]=None, diameter: float=0, **kwargs) -> Circle:
        if isinstance(id, Circle):
            circle = id
            circle.parent = self
            self.circles[circle.id] = circle
        else:
            if mid is None:
                mid = [0, 0]
            circle = Circle(id=id, mid=mid, diameter=diameter, **kwargs)
            circle.parent = self
            self.circles[id] = circle
        return circle

    def add_group(self, id: Union["Group", str], **kwargs) -> "Group":
        if isinstance(id, Group):
            group = id
            group.parent = self
            self.groups[group.id] = group
            return group
        else:
            group = Group(id=id, **kwargs)
            group.parent = self
            self.groups[group.id] = group
            return group

    def to_dict(self) -> dict:
        # Always ensure a leading "/" for references.
        def process_ref(ref):
            if isinstance(ref, str) and not ref.startswith('/'):
                return '/' + ref
            return ref

        group_dict = {
            "id": self.id,
            "name": self.name,
            "fullPath": self.fullPath,
            "points": {k: {**asdict_no_parent(v), "fullPath": v.fullPath} for k, v in self.points.items()},
            "agents": {k: {**asdict_no_parent(v), "fullPath": v.fullPath} for k, v in self.agents.items()},
            "visionagents": {k: {**asdict_no_parent(v), "fullPath": v.fullPath} for k, v in self.visionagents.items()},
            "vectors": {k: {**asdict_no_parent(v), "fullPath": v.fullPath} for k, v in self.vectors.items()},
            "coordinate_systems": {k: {**asdict_no_parent(v), "fullPath": v.fullPath} for k, v in
                                   self.coordinate_systems.items()},
            "lines": {k: {**asdict_no_parent(v),
                          "start": process_ref(v._start_element.fullPath if v._start_element is not None else v.start),
                          "end": process_ref(v._end_element.fullPath if v._end_element is not None else v.end),
                          "fullPath": v.fullPath}
                      for k, v in self.lines.items()},
            "rectangles": {k: {**asdict_no_parent(v), "fullPath": v.fullPath} for k, v in self.rectangles.items()},
            "circles": {k: {**asdict_no_parent(v), "fullPath": v.fullPath} for k, v in self.circles.items()},
            "groups": {k: v.to_dict() for k, v in self.groups.items()},
        }
        return group_dict

    def clear(self):
        self.points.clear()
        self.agents.clear()
        self.visionagents.clear()
        self.vectors.clear()
        self.coordinate_systems.clear()
        self.lines.clear()
        self.rectangles.clear()
        self.circles.clear()
        self.groups.clear()


# -----------------------------------------------------------------------------
# Dynamic2DPlotter Class
# -----------------------------------------------------------------------------

class FRODO_Web_Interface:
    server: SyncWebsocketServer
    html_file_path: str = "./frodo_web_gui_new.html"
    _thread: threading.Thread
    _exit: bool = False
    videos: dict

    def __init__(self):
        self.server = SyncWebsocketServer(host="localhost", port=8000)
        self.default_group = Group(id="default")
        self.videos = {}
        self._thread = threading.Thread(target=self._task, daemon=True)
        register_exit_callback(self.close)

    def add_point(self, id: str, x: float, y: float, **kwargs) -> Point:
        return self.default_group.add_point(id, x, y, **kwargs)

    def add_agent(self, id: str, position: List[float], psi: float, **kwargs) -> Agent:
        return self.default_group.add_agent(id, position, psi, **kwargs)

    def add_vision_agent(self, id: str, position: List[float], psi: float, vision_radius: float, vision_fov: float,
                         **kwargs) -> VisionAgent:
        return self.default_group.add_vision_agent(id, position, psi, vision_radius, vision_fov, **kwargs)

    def add_vector(self, id: str, origin: List[float], vec: List[float], **kwargs) -> Vector:
        return self.default_group.add_vector(id, origin, vec, **kwargs)

    def add_coordinate_system(self, id: str, origin: List[float], ex: List[float], ey: List[float],
                              **kwargs) -> CoordinateSystem:
        return self.default_group.add_coordinate_system(id, origin, ex, ey, **kwargs)

    def add_line(self, id: str, start: Union[str, List[float], object], end: Union[str, List[float], object],
                 **kwargs) -> Line:
        return self.default_group.add_line(id, start, end, **kwargs)

    def add_rectangle(self, id: str, mid: List[float], x: float, y: Optional[float] = None, **kwargs) -> Rectangle:
        return self.default_group.add_rectangle(id, mid, x, y, **kwargs)

    def add_circle(self, id: str, mid: List[float], diameter: float, **kwargs) -> Circle:
        return self.default_group.add_circle(id, mid, diameter, **kwargs)

    def add_video(self, id: str, address: str, port: int, placeholder: bool = False):
        self.videos[id] = Video(id=id, title=id, address=address, port=port, placeholder=placeholder)

    def add_group(self, id: Union[Group, str], **kwargs) -> Group:
        if isinstance(id, Group):
            group = id
            group.parent = self.default_group
            self.default_group.groups[group.id] = group
            return group
        else:
            return self.default_group.add_group(id, **kwargs)

    def get_element_by_id(self, path: str) -> Optional[Any]:
        return self.default_group.get_element_by_id(path)

    def remove_element_by_id(self, path: str) -> Optional[Any]:
        return self.default_group.remove_element_by_id(path)

    def get_data(self) -> dict:
        return {"groups": {self.default_group.id: self.default_group.to_dict()},
                "videos": {k: asdict_no_parent(v) for k, v in self.videos.items()}}

    def _task(self):
        while not self._exit:
            data: dict = self.get_data()
            self.server.send(data)
            time.sleep(0.05)

    def _open_plotter_html(self) -> bool:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(current_dir, self.html_file_path)
        try:
            if not os.path.exists(html_path):
                print(f"Error: File {html_path} does not exist.")
                return False
            webbrowser.open(f'file://{html_path}', new=2)
            return True
        except Exception as e:
            print(f"Error opening file: {e}")
            return False

    def start(self):
        self.server.start()
        self._thread.start()
        self._open_plotter_html()

    def close(self, *args, **kwargs):
        data = {'command': "close_browser"}
        self.server.send(data)
        self._exit = True
        if self._thread is not None and self._thread.is_alive():
            self._thread.join()


# ======================================================================================================================
if __name__ == '__main__':
    plotter = FRODO_Web_Interface()

    # Example: Add some elements to the default group.
    p1 = plotter.add_point("p1", 1.0, 2.0, color=[1, 0, 0], size=1)
    p2 = plotter.add_point("p2", 1.0, -2.0, color=[1, 0, 0], size=0.2)

    # Create a group object and add elements to it.
    group = Group(id="group1")
    a1 = group.add_agent("a1", [3.0, 4.0], psi=0.5, color=[0, 1, 1], size=1)
    va1 = group.add_vision_agent("va1", [5.0, 6.0], psi=0.0, vision_radius=2.0, vision_fov=2, color=[0, 0, 1])
    p22 = plotter.add_point("p22", 10.0, -2.0, color=[1, 0, 0], size=0.2)
    # Here we add a line using element objects (va1 and p22) so that the line's endpoints are stored dynamically.
    group.add_line("line1", va1, a1)
    plotter.add_group(group)

    plotter.add_video("FRODO 1", "frodo1", 5000, placeholder=False)
    plotter.add_video("FRODO 2", "frodo2", 5000, placeholder=False)
    plotter.add_video("FRODO 3", "frodo3", 5000, placeholder=False)
    plotter.add_video("FRODO 4", "frodo4", 5000, placeholder=False)

    # Also add a line from a point in the default group to an element in group1.
    # Example (uncomment if desired):
    # plotter.add_line("line2", p1, va1, color=[0, 0, 0])

    plotter.start()

    # Keep the main thread alive.
    while True:
        # Animate a change in position:
        a1.position[0] += 0.01
        va1.position[0] += 0.02
        time.sleep(0.1)
