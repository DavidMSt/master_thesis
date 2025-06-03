import dataclasses
import time
import math

from applications.FRODO.utilities.uncertainty.uncertainty import uncertainty_distance, uncertainty_angle
from applications.FRODO.utilities.web_gui.FRODO_Web_Interface import VisionAgent, Circle
from robots.frodo.frodo import Frodo
from core.utils.teleplot import sendValue
from robots.frodo.frodo_definitions import frodo_colors
from core.utils.time import PrecisionTimer

''''''


@dataclasses.dataclass
class FRODO_Sample:
    ...


@dataclasses.dataclass
class FRODO_State:
    x: float = 0
    y: float = 0
    psi: float = 0
    v: float = 0
    psi_dot: float = 0


@dataclasses.dataclass
class FRODO_Aruco_Measurements:
    marker_id: int = -1
    translation_vec: list[float] = dataclasses.field(default_factory=list)
    tvec_uncertainty: float = 0.0
    psi: float = 0.0
    psi_uncertainty: float = 0.0


@dataclasses.dataclass
class FRODO_Measurement_Data:
    id: str = "none"
    time: float = 0.0

    speed_l: float = 0.0
    speed_r: float = 0.0
    rpm_l: float = 0.0
    rpm_r: float = 0.0

    aruco_measurements: list[FRODO_Aruco_Measurements] = dataclasses.field(default_factory=list)


# ======================================================================================================================
class FRODO_Agent:
    id: str

    state_estimated: FRODO_State
    state_true: FRODO_State
    measurements: FRODO_Measurement_Data

    estimated_plot_item: VisionAgent
    estimated_plot_covariance: Circle

    robot: Frodo

    _last_update_time: float = 0

    def __init__(self, id: str, robot: Frodo):
        self.id = id
        self.robot = robot
        self.state_estimated = FRODO_State(0, 0, 0, 0, 0)
        self.state_true = FRODO_State(0, 0, 0, 0, 0)
        self.measurements = FRODO_Measurement_Data()
        self._last_update_time = 0

        self.estimated_plot_item = VisionAgent(f'{id}_est',
                                               vision_fov=0,
                                               vision_radius=0,
                                               position=[0, 0],
                                               psi=0,
                                               color=frodo_colors[self.id])

        self.estimated_plot_covariance = Circle(
            f'{id}_cov',
            mid=[0, 0],
            diameter=0,
            fill=frodo_colors[self.id],
            alpha=0.2
        )

        self.robot.callbacks.stream.register(self._robot_stream_callback)
        # Buffer to hold high-frequency state measurements: each element is (timestamp, FRODO_State)
        self._state_buffer = []

    # ------------------------------------------------------------------------------------------------------------------
    def readRobotData(self):
        data = self.robot.getData()
        if data is not None:
            self.measurements.id = data['general']['id']
            self.measurements.time = data['general']['time']

            self.measurements.speed_l = data['sensors']['speed_left']
            self.measurements.speed_r = data['sensors']['speed_right']
            self.measurements.rpm_l = data['sensors']['rpm_left']
            self.measurements.rpm_r = data['sensors']['rpm_right']

            self.measurements.aruco_measurements = []
            for measurement in data['sensors']['aruco_measurements']:
                tvec_unc = uncertainty_distance(float(measurement['translation_vec'][0]),
                                                float(measurement['translation_vec'][1]))
                psi_unc = uncertainty_angle(float(measurement['translation_vec'][0]),
                                            float(measurement['translation_vec'][1]))
                tmp = FRODO_Aruco_Measurements(marker_id=measurement['id'],
                                               translation_vec=measurement['translation_vec'],
                                               tvec_uncertainty=tvec_unc,
                                               psi=measurement['psi'],
                                               psi_uncertainty=psi_unc
                                               )
                self.measurements.aruco_measurements.append(tmp)
        else:
            print(f"Robot {self.id} data: None")

    # ------------------------------------------------------------------------------------------------------------------
    def updateRealState(self, x, y, psi):
        current_time = time.perf_counter()
        new_state = FRODO_State(x, y, psi, 0, 0)

        # Append the new measurement (with its timestamp) to the buffer.
        self._state_buffer.append((current_time, new_state))

        # Keep only the samples within the desired window duration (here 50 ms ~20Hz output).
        window_duration = 0.05  # 50 milliseconds
        self._state_buffer = [(t, s) for (t, s) in self._state_buffer if (current_time - t) <= window_duration]

        # Only compute derivatives if we have at least two samples.
        if len(self._state_buffer) >= 2:
            t0, state0 = self._state_buffer[0]
            t1, state1 = self._state_buffer[-1]
            dt_window = t1 - t0

            if dt_window > 0:
                # Compute displacement in the global frame.
                dx = state1.x - state0.x
                dy = state1.y - state0.y

                # Compute an average heading between the two samples.
                # This average is used to project the displacement into the robot's forward direction.
                avg_heading = math.atan2(
                    math.sin(state0.psi) + math.sin(state1.psi),
                    math.cos(state0.psi) + math.cos(state1.psi)
                )

                # Project displacement onto the robot's forward axis.
                # This yields a signed displacement: positive if moving forward, negative if moving backward.
                displacement_forward = dx * math.cos(avg_heading) + dy * math.sin(avg_heading)
                v_raw = displacement_forward / dt_window

                # Compute the change in orientation, wrapped to [-pi, pi].
                dpsi = state1.psi - state0.psi
                dpsi = math.atan2(math.sin(dpsi), math.cos(dpsi))
                psi_dot_raw = dpsi / dt_window

                # Apply a simple exponential low-pass filter to the velocity estimates.
                alpha = 0.2  # Smoothing factor (tune as needed)
                self.state_true.v = alpha * v_raw + (1 - alpha) * self.state_true.v
                self.state_true.psi_dot = alpha * psi_dot_raw + (1 - alpha) * self.state_true.psi_dot

            # Optionally, smooth the position and heading using the buffer.
            avg_x = sum(s.x for _, s in self._state_buffer) / len(self._state_buffer)
            avg_y = sum(s.y for _, s in self._state_buffer) / len(self._state_buffer)
            avg_psi = math.atan2(
                sum(math.sin(s.psi) for _, s in self._state_buffer),
                sum(math.cos(s.psi) for _, s in self._state_buffer)
            )
            self.state_true.x = avg_x
            self.state_true.y = avg_y
            self.state_true.psi = avg_psi

        # Update the timestamp for the next call.
        self._last_update_time = current_time

        sendValue(f'robot_{self.id}_v', self.state_true.v)
        sendValue(f'robot_{self.id}_psidot', self.state_true.psi_dot)

    # ------------------------------------------------------------------------------------------------------------------
    def _robot_stream_callback(self, stream, *args, **kwargs):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def __del__(self):
        print(f"Deleting agent {self.id}")
