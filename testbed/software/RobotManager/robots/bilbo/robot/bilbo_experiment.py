import dataclasses
import math
import numpy as np

# === CUSTOM PACKAGES ==================================================================================================
from robots.bilbo.robot.bilbo_core import BILBO_Core
from core.utils.data import generate_time_vector, generate_random_input
from robots.bilbo.robot.bilbo_definitions import BILBO_Control_Mode, BILBO_CONTROL_DT, MAX_STEPS_TRAJECTORY
from core.utils.events import event_definition, ConditionEvent, waitForEvents
from core.utils.plotting import UpdatablePlot
from core.utils.sound.sound import speak, playSound


# ======================================================================================================================
@event_definition
class BILBO_Experiments_Events:
    finished: ConditionEvent = ConditionEvent(flags=[('trajectory_id', int)])
    aborted: ConditionEvent = ConditionEvent(flags=[('trajectory_id', int)])


# ======================================================================================================================
@dataclasses.dataclass
class BILBO_TrajectoryInput:
    step: int
    left: float
    right: float


# ======================================================================================================================
@dataclasses.dataclass
class BILBO_Trajectory:
    name: str
    id: int
    length: int
    time_vector: np.ndarray
    control_mode: BILBO_Control_Mode
    inputs: dict[int, BILBO_TrajectoryInput]


# ======================================================================================================================
class BILBO_Experiments:

    def __init__(self, core: BILBO_Core):
        self.core = core
        self.id = id
        self.logger = self.core.logger
        self.device = self.core.device

        self.events = BILBO_Experiments_Events()
        self.device.events.event.on(self._trajectory_event_callback, flags={'event': 'trajectory'})

    # ------------------------------------------------------------------------------------------------------------------
    def runTestTrajectories(self, num, time, frequency=2, gain=0.25):
        t_vector = generate_time_vector(start=0, end=time, dt=BILBO_CONTROL_DT)

        if len(t_vector) > MAX_STEPS_TRAJECTORY:
            self.logger.warning("Trajectory too long")
            return None

        input = generate_random_input(t_vector=t_vector, f_cutoff=frequency, sigma_I=gain)
        outputs = []

        speak(f"{self.id}: Test Trajectory Program with {num} trajectories")

        index = 0

        plot = UpdatablePlot(x_label='time', y_label='theta', xlim=[0, t_vector[-1]])

        while index < num:
            trajectory_id = index + 1
            self.core.interface_events.resume.wait(timeout=None)
            playSound('notification')

            speak(f"{self.id}: Start trajectory {trajectory_id} of {num}")

            trajectory = self.generateTrajectory(inputs=input,
                                                 name=f"Test Trajectory {trajectory_id}",
                                                 id=trajectory_id,
                                                 control_mode=BILBO_Control_Mode.BALANCING)

            data = self.runTrajectory(trajectory=trajectory)

            if data is not None:
                output = (data['output']['lowlevel.estimation.state.theta'])
            else:
                print("NO DATA")
                return

            plot.appendPlot(x=t_vector, y=output, label=f"Trajectory {trajectory_id}")

            result = waitForEvents(
                events=[
                    self.core.interface_events.resume,
                    self.core.interface_events.revert
                ]
            )

            if result == self.core.interface_events.resume:
                index += 1
                playSound('notification')
                speak(f"{self.id}: Trajectory {trajectory_id} saved")
                outputs.append(output)

            elif result == self.core.interface_events.revert:
                plot.removePlot(last=True)
                speak(f"{self.id}: Trajectory {trajectory_id} deleted")
            else:
                raise Exception("Unknown event waiting result")

        speak(f"{self.id}: Finished test trajectories")

        trajectory_reference = np.asarray(outputs[0])

        for i in range(num - 1):
            trajectory_i = np.asarray(outputs[i + 1])
            rms_error = np.sqrt(np.mean((trajectory_reference - trajectory_i) ** 2))
            mae_error = np.mean(np.abs(trajectory_reference - trajectory_i))
            print(f"RMS error between trajectory 1 and trajectory {i + 2}: {math.degrees(rms_error):.4f}")
            print(f"MAE error between trajectory 1 and trajectory {i + 2}: {math.degrees(mae_error):.4f}")

    # ------------------------------------------------------------------------------------------------------------------
    def runTrajectory(self, trajectory: BILBO_Trajectory, signals: list[str] = None):
        assert (len(trajectory.inputs) <= MAX_STEPS_TRAJECTORY)
        assert (trajectory.length == len(trajectory.inputs))
        assert (trajectory.time_vector.shape[0] == trajectory.length)

        self.logger.info(f"Running trajectory {trajectory.name}, ID: {trajectory.id}")
        # speak(f"{self.id}: Run trajectory {trajectory.name} , ID: {trajectory.id}")

        if signals is None:
            signals = ['lowlevel.estimation.state.v',
                       'lowlevel.estimation.state.theta',
                       'lowlevel.estimation.state.theta_dot',
                       'lowlevel.estimation.state.psi',
                       'lowlevel.estimation.state.psi_dot']

        self.device.function(
            function='runTrajectory',
            data={
                'trajectory_id': trajectory.id,
                'input': [[float(input.left), float(input.right)] for input in trajectory.inputs.values()],
                'signals': signals
            },
        )
        success = self.events.finished.wait(flags={'trajectory_id': trajectory.id},
                                            timeout=trajectory.time_vector[-1] + 2)  # type:ignore

        if not success:
            self.logger.error(f"Trajectory {trajectory.name} failed")
            self.events.aborted.set(resource=trajectory, flags={'trajectory_id': trajectory.id})
            return None

        data = self.events.finished.get_data()

        return data

    # ------------------------------------------------------------------------------------------------------------------
    def generateTrajectory(self, inputs: list, name: str, id: int, control_mode: BILBO_Control_Mode):
        assert (len(inputs) <= MAX_STEPS_TRAJECTORY)

        trajectory_inputs = {}

        for i, input in enumerate(inputs):
            if isinstance(input, list):
                input_left = float(input[0])
                input_right = float(input[1])
            else:
                input_left = float(input) / 2
                input_right = float(input) / 2

            trajectory_inputs[i] = BILBO_TrajectoryInput(
                step=i,
                left=input_left,
                right=input_right,
            )

        trajectory = BILBO_Trajectory(
            name=name,
            id=id,
            length=len(inputs),
            time_vector=generate_time_vector(start=0, end=(len(inputs) - 1) * BILBO_CONTROL_DT, dt=BILBO_CONTROL_DT),
            control_mode=control_mode,
            inputs=trajectory_inputs,
        )

        return trajectory

    # ------------------------------------------------------------------------------------------------------------------
    def startTrajectory(self):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def sendTrajectory(self):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def stopTrajectory(self):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def _trajectory_event_callback(self, message, *args, **kwargs):
        if not 'event' in message.data:
            self.logger.error(f"Robot {self.id}: Received trajectory event without event field")

        if message.data['event'] == 'finished':
            self.logger.info(f"Trajectory {message.data['trajectory_id']} finished. Len: {len(message.data['input'])}")
            speak(f"{self.id}: Trajectory {message.data['trajectory_id']} finished")

            self.events.finished.set(resource=message.data, flags={'trajectory_id': message.data['trajectory_id']})
