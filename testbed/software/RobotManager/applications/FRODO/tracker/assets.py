import abc
import dataclasses
import math
from abc import ABC

import numpy as np

from extensions.optitrack.optitrack import RigidBodySample
from core.utils.orientation.orientation_2d import calculate_projection, calculate_rotation_angle, \
    fix_coordinate_axes


class TrackedAsset(ABC):
    name: str
    tracking_valid: bool

    reference_coordinate_system: None

    @abc.abstractmethod
    def update(self, data):
        ...


# ======================================================================================================================
@dataclasses.dataclass
class TrackedVisionRobot_Definition:
    points: list[int]
    point_y_axis_start: int
    point_y_axis_end: int
    point_x_axis_project: int


class TrackedVisionRobot(TrackedAsset):
    position: np.ndarray
    psi: float
    definition: TrackedVisionRobot_Definition

    x_axis: np.ndarray
    y_axis: np.ndarray

    def __init__(self, name, definition: TrackedVisionRobot_Definition):
        self.name = name
        self.definition = definition
        self.tracking_valid = False
        self.position = np.zeros(2)
        self.x_axis = np.zeros(2)
        self.y_axis = np.zeros(2)
        self.psi = 0

    def update(self, data: RigidBodySample):
        # Check if the tracking is valid
        if not data.valid:
            self.tracking_valid = False
            self.position = np.zeros(2)
            self.x_axis = np.zeros(2)
            self.y_axis = np.zeros(2)
            self.psi = 0
            return

        # First calculate the robots values in the optitrack coordinate systems

        # Get the y-axis points
        y_axis_point_start = np.asarray(data.markers[self.definition.point_y_axis_start][0:2])
        y_axis_point_end = np.asarray(data.markers[self.definition.point_y_axis_end][0:2])

        # Get the x-axis point for projection
        x_axis_point_start = np.asarray(data.markers[self.definition.point_x_axis_project][0:2])

        # Get the projected center point
        center_point = calculate_projection(y_axis_point_start, y_axis_point_end, x_axis_point_start)

        self.position = center_point
        self.x_axis = center_point - x_axis_point_start
        self.y_axis = y_axis_point_end - y_axis_point_start

        psi = calculate_rotation_angle(vector=self.x_axis)

        self.psi = psi

        self.tracking_valid = True


# ======================================================================================================================
@dataclasses.dataclass
class TrackedOrigin_Definition:
    points: list[int]
    origin: int
    x_axis_end: int
    y_axis_end: int


class TrackedOrigin(TrackedAsset):
    position: np.ndarray
    x_axis: np.ndarray
    y_axis: np.ndarray
    psi: float

    def __init__(self, name, definition: TrackedOrigin_Definition):
        self.name = name
        self.definition = definition
        self.tracking_valid = False
        self.position = np.zeros(2)
        self.x_axis = np.zeros(2)
        self.y_axis = np.zeros(2)
        self.psi = 0

    def update(self, data: RigidBodySample):
        # Check if tracking is valid
        if not data.valid:
            self.tracking_valid = False
            self.position = np.zeros(2)
            self.x_axis = np.zeros(2)
            self.y_axis = np.zeros(2)
            return

        self.position = np.asarray(data.markers[self.definition.origin][0:2])
        self.x_axis =  np.asarray(data.markers[self.definition.x_axis_end][0:2]) - self.position
        y_axis_raw =  np.asarray(data.markers[self.definition.y_axis_end][0:2]) - self.position

        # Normalize the axes to 1
        self.x_axis = self.x_axis / np.linalg.norm(self.x_axis)
        y_axis_raw = y_axis_raw / np.linalg.norm(y_axis_raw)

        _, y_axis = fix_coordinate_axes(self.x_axis, y_axis_raw, 'x')
        self.y_axis = y_axis / np.linalg.norm(y_axis)

        self.psi = calculate_rotation_angle(vector=self.x_axis)
        self.tracking_valid = True


# ======================================================================================================================
vision_robot_application_assets = {
    'frodo1': TrackedVisionRobot('frodo1', TrackedVisionRobot_Definition(points=[1, 2, 3, 4, 5],
                                                                         point_y_axis_start=5,
                                                                         point_y_axis_end=3,
                                                                         point_x_axis_project=2)),
    'frodo2': TrackedVisionRobot('frodo2', TrackedVisionRobot_Definition(points=[1, 2, 3, 4, 5],
                                                                         point_y_axis_start=1,
                                                                         point_y_axis_end=2,
                                                                         point_x_axis_project=3)),
    'frodo3': TrackedVisionRobot('frodo3', TrackedVisionRobot_Definition(points=[1, 2, 3, 4, 5],
                                                                         point_y_axis_start=4,
                                                                         point_y_axis_end=2,
                                                                         point_x_axis_project=5)),
    'static1': TrackedOrigin('static1', TrackedOrigin_Definition(points=[1, 2, 3, 4, 5],
                                                                 origin=3,
                                                                 x_axis_end=1,
                                                                 y_axis_end=4)),

    'static2': TrackedOrigin('static2', TrackedOrigin_Definition(points=[1, 2, 3, 4, 5],
                                                                 origin=1,
                                                                 x_axis_end=5,
                                                                 y_axis_end=4))
}
