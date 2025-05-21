import numpy as np

from robot.bilbo import BILBO
from robot.dynamics.tests.sys_id import estimate_system_and_lifted_matrix
from robot.experiment.bilbo_experiment import BILBO_Trajectory


def run_system_identification(bilbo: BILBO, trials, duration, frequencies, gains, wait_for_resume=True):
    learning_inputs = []
    learning_outputs = []

    if (len(frequencies) != trials) or (len(gains) != trials):
        raise ValueError(
            "The number of frequencies and gains must be equal to the number of trials."
        )

    for i in range(0, trials):

        # Generate Test Trajectory
        frequency = frequencies[i]
        gain = gains[i]
        trajectory: BILBO_Trajectory = bilbo.experiment_handler.generateTestTrajectory(id=i + 1, time=duration,
                                                                                       frequency=frequency, gain=gain)

        input = np.asarray([i.left/2 + i.right/2 for i in trajectory.inputs.values()])
        learning_inputs.append(input)

        # TODO: Add waiting for a resume signal
        if wait_for_resume:
            ...

            estimate_system_and_lifted_matrix()

        data = bilbo.experiment_handler.runTrajectory(trajectory, signals='lowlevel.estimation.state.theta')
        learning_outputs.append(np.asarray(data['output']['lowlevel.estimation.state.theta']))
        bilbo.board.beep()

