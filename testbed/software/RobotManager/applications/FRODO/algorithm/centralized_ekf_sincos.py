import dataclasses
import math
import numpy as np
import qmt

from core.utils.logging_utils import Logger

logger = Logger('EKF')
logger.setLevel("INFO")

AGENT_STATE_DIM = 4
INDEX_X = 0
INDEX_Y = 1
INDEX_SIN = 2
INDEX_COS = 3

INDEX_PSI = 2

INDEX_V = 0
INDEX_PSIDOT = 1


def unscented_transform_psi_to_sin_cos(mean_psi: float, var_psi: float):
    """
    Applies the unscented transform to compute the mean and covariance of [sin(ψ), cos(ψ)]
    from the mean and variance of ψ.
    """

    # UT parameters
    n = 1  # dimension of ψ
    alpha = 1e-3
    beta = 2.0
    kappa = 0.0
    lambda_ = alpha ** 2 * (n + kappa) - n

    # Weights
    wm = np.zeros(2 * n + 1)
    wc = np.zeros(2 * n + 1)
    wm[0] = lambda_ / (n + lambda_)
    wc[0] = lambda_ / (n + lambda_) + (1 - alpha ** 2 + beta)
    for i in range(1, 2 * n + 1):
        wm[i] = wc[i] = 1.0 / (2 * (n + lambda_))

    # Sigma points for ψ
    sqrt_c = np.sqrt((n + lambda_) * var_psi)
    sigma_points = np.array([
        mean_psi,
        mean_psi + sqrt_c,
        mean_psi - sqrt_c
    ])

    # Transform to [sin(ψ), cos(ψ)]
    transformed = np.array([[np.sin(psi), np.cos(psi)] for psi in sigma_points])  # shape (3, 2)

    # Mean
    mean_trans = np.sum(wm[:, np.newaxis] * transformed, axis=0)

    # Covariance
    diff = transformed - mean_trans
    cov_trans = sum(wc[i] * np.outer(diff[i], diff[i]) for i in range(2 * n + 1))

    return mean_trans, cov_trans


# ----------------------------------------------------------------------------------------------------------------------
@dataclasses.dataclass
class VisionAgent:
    id: str
    index: int
    state: np.ndarray
    # state_augmented: np.ndarray
    state_covariance: np.ndarray
    # state_covariance_augmented: np.ndarray
    input: np.ndarray
    input_covariance: np.ndarray
    measurements: list['VisionAgentMeasurement']
    dynamics_noise: float

    @property
    def state_augmented(self):
        return np.array([
            self.state[0],
            self.state[1],
            np.sin(self.state[2]),
            np.cos(self.state[2]),
        ])

    # @property
    # def state_covariance_augmented(self):
    #     J = np.array([
    #         [1, 0, 0],
    #         [0, 1, 0],
    #         [0, 0, np.cos(self.state[2])],
    #         [0, 0, -np.sin(self.state[2])]
    #     ])
    #
    #     return J @ self.state_covariance @ J.T

    @property
    def state_covariance_augmented(self):
        # Extract heading mean and variance
        psi_hat = self.state[2]
        P = self.state_covariance
        var_psi = P[2, 2]

        # First-order Jacobian
        J = np.array([
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, np.cos(psi_hat)],
            [0, 0, -np.sin(psi_hat)]
        ])

        # Initial linearized covariance
        P_aug = J @ P @ J.T

        # Second-order corrections for sin(psi) and cos(psi)
        sin_psi = np.sin(psi_hat)
        cos_psi = np.cos(psi_hat)

        var_sin = (cos_psi ** 2) * var_psi + 0.5 * (sin_psi ** 2) * (var_psi ** 2)
        var_cos = (sin_psi ** 2) * var_psi + 0.5 * (cos_psi ** 2) * (var_psi ** 2)

        # Optional: Covariance between sin and cos (can be helpful if needed)
        cov_sin_cos = -sin_psi * cos_psi * var_psi \
                      + 0.5 * sin_psi * cos_psi * (cos_psi ** 2 - sin_psi ** 2) * (var_psi ** 2)

        # Apply the corrections
        P_aug[2, 2] = var_sin
        P_aug[3, 3] = var_cos
        P_aug[2, 3] = cov_sin_cos
        P_aug[3, 2] = cov_sin_cos  # symmetric

        return P_aug


# ----------------------------------------------------------------------------------------------------------------------
@dataclasses.dataclass
class VisionAgentMeasurement:
    source: str
    source_index: int
    target: str
    target_index: int
    measurement: np.ndarray
    measurement_covariance: np.ndarray

    @property
    def measurement_augmented(self):
        return np.array([
            self.measurement[0],
            self.measurement[1],
            np.sin(self.measurement[2]),
            np.cos(self.measurement[2]),
        ])

    # @property
    # def measurement_covariance_augmented(self):
    #     # Extract heading mean and variance
    #     psi_hat = self.measurement[2]
    #     P = self.measurement_covariance
    #     var_psi = P[2, 2]
    #
    #     # First-order Jacobian
    #     J = np.array([
    #         [1, 0, 0],
    #         [0, 1, 0],
    #         [0, 0, np.cos(psi_hat)],
    #         [0, 0, -np.sin(psi_hat)]
    #     ])
    #
    #     # Initial linearized covariance
    #     P_aug = J @ P @ J.T
    #
    #     # Second-order corrections for sin(psi) and cos(psi)
    #     sin_psi = np.sin(psi_hat)
    #     cos_psi = np.cos(psi_hat)
    #
    #     var_sin = (cos_psi ** 2) * var_psi + 0.5 * (sin_psi ** 2) * (var_psi ** 2)
    #     var_cos = (sin_psi ** 2) * var_psi + 0.5 * (cos_psi ** 2) * (var_psi ** 2)
    #
    #     # Optional: Covariance between sin and cos (can be helpful if needed)
    #     cov_sin_cos = -sin_psi * cos_psi * var_psi \
    #                   + 0.5 * sin_psi * cos_psi * (cos_psi ** 2 - sin_psi ** 2) * (var_psi ** 2)
    #
    #     # Apply the corrections
    #     P_aug[2, 2] = var_sin
    #     P_aug[3, 3] = var_cos
    #     P_aug[2, 3] = cov_sin_cos
    #     P_aug[3, 2] = cov_sin_cos  # symmetric
    #
    #     return P_aug
    @property
    def measurement_covariance_augmented(self):
        P = self.measurement_covariance
        psi_hat = self.measurement[2]
        var_psi = P[2, 2]

        _, cov_sin_cos = unscented_transform_psi_to_sin_cos(psi_hat, var_psi)

        # Build full 4x4 augmented covariance matrix
        P_aug = np.zeros((4, 4))
        P_aug[0, 0] = P[0, 0]
        P_aug[1, 1] = P[1, 1]
        P_aug[2:4, 2:4] = cov_sin_cos

        return P_aug


# ----------------------------------------------------------------------------------------------------------------------
class CentralizedLocationAlgorithm:
    agents: dict[str, VisionAgent]

    Ts: float
    state: np.ndarray
    state_covariance: np.ndarray
    step: int = 0

    def __init__(self, Ts):
        self.Ts = Ts

    # ------------------------------------------------------------------------------------------------------------------
    def init(self, agents: dict[str, VisionAgent]):
        self.agents = agents

        # Build the state:
        self.state = np.zeros(len(agents) * AGENT_STATE_DIM)

        for i, agent in enumerate(agents.values()):
            self.state[i * AGENT_STATE_DIM:(i + 1) * AGENT_STATE_DIM] = agent.state_augmented

        logger.info(f"State: {self.state}")

        # Build the state covariance
        self.state_covariance = np.zeros((len(agents) * 4, len(agents) * 4))
        for i, agent in enumerate(agents.values()):
            self.state_covariance[i * AGENT_STATE_DIM:(i + 1) * AGENT_STATE_DIM,
            i * AGENT_STATE_DIM:(i + 1) * AGENT_STATE_DIM] = agent.state_covariance_augmented

        logger.info(f"State covariance: {self.state_covariance}")

        pass

    # ------------------------------------------------------------------------------------------------------------------
    def update(self):

        # STEP 1: PREDICTION
        x_hat_pre, P_hat_pre = self.prediction()

        # STEP 2: EXTRACT MEASUREMENTS
        measurements = self.getMeasurements()
        measurement_list = [f"{measurement.source}->{measurement.target}" for measurement in measurements]

        if len(measurements) > 0:

            if self.step == 30:
                pass

            # STEP 3: CALCULATE SPARSE MEASUREMENT JACOBIAN
            H = self.measurementJacobian_sparse(measurements)

            # H[:,0:4] = np.zeros((4,4))
            # STEP 4: CALCULATE THE KALMAN GAIN
            W = self.buildMeasurementCovariance_sparse(measurements)
            K = P_hat_pre @ H.T @ np.linalg.inv(H @ P_hat_pre @ H.T + W)

            # STEP 5: BUILD THE MEASUREMENT VECTOR
            y = self.buildMeasurementVector_sparse(measurements)

            # STEP 6: BUILD THE PREDICTED MEASUREMENT VECTOR
            y_est = self.measurementPrediction_sparse(measurements)

            # STEP 7: UPDATE
            diff = y - y_est

            correction_term = K @ diff
            new_state = x_hat_pre + K @ diff
            new_covariance = (np.eye(len(self.agents) * AGENT_STATE_DIM) - K @ H) @ P_hat_pre @ (
                    np.eye(len(self.agents) * AGENT_STATE_DIM) - K @ H).T + K @ W @ K.T

            pass
        else:
            new_state = x_hat_pre
            new_covariance = P_hat_pre

        self.state = new_state
        self.state_covariance = new_covariance

        # # Write the state back to the agents
        for i in range(len(self.agents)):
            agent = self.getAgentByIndex(i)
            if agent is None:
                raise ValueError(f"Agent with index {i} does not exist.")

            state = self.state[i * AGENT_STATE_DIM:(i + 1) * AGENT_STATE_DIM]
            agent.state[INDEX_X] = state[INDEX_X]
            agent.state[INDEX_Y] = state[INDEX_Y]
            agent.state[INDEX_PSI] = np.arctan2(state[INDEX_SIN], state[INDEX_COS])

            state_covariance_aug = self.state_covariance[i * AGENT_STATE_DIM:(i + 1) * AGENT_STATE_DIM,
                                   i * AGENT_STATE_DIM:(i + 1) * AGENT_STATE_DIM]

            J = np.array([
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, state[INDEX_COS], -state[INDEX_SIN]],
            ])

            agent.state_covariance = J @ state_covariance_aug @ J.T

        self.step += 1

        if (self.step % 10) == 0 or self.step == 1:
            print("--------------------------------")
            print(f"Step: {self.step}")
            for agent in self.agents.values():
                print(
                    f"{agent.id}: \t x: {agent.state[0]:.3f} \t y: {agent.state[1]:.3f} \t psi: {agent.state[2]:.2f} \t Cov: {np.linalg.norm(agent.state_covariance, 'fro'):.1f}")

            pass

    # ------------------------------------------------------------------------------------------------------------------
    # def augmentAgentState(self, state):
    #
    #     state = np.asarray(state)
    #     assert (len(state) == 3)
    #
    #     augmented_state = np.array([
    #         state[0],
    #         state[1],
    #         np.sin(state[2]),
    #         np.cos(state[2]),
    #     ])
    #
    #     return augmented_state

    # ------------------------------------------------------------------------------------------------------------------
    def augmentAgentCovariance(self, covariance):
        return covariance

    # ------------------------------------------------------------------------------------------------------------------
    def predictionAgent(self, state: np.ndarray, input: np.ndarray):
        """
        Prediction step of one agent
        Args:
            state: State of the agent
            input: Input to the agent

        Returns:

        """
        state_hat = np.array([
            state[INDEX_X] + self.Ts * input[INDEX_V] * state[INDEX_COS],
            state[INDEX_Y] + self.Ts * input[INDEX_V] * state[INDEX_SIN],
            state[INDEX_SIN] + self.Ts * input[INDEX_PSIDOT] * state[INDEX_COS],
            state[INDEX_COS] - self.Ts * input[INDEX_PSIDOT] * state[INDEX_SIN]
        ])
        return state_hat

    # ------------------------------------------------------------------------------------------------------------------
    def enumerateAgentArray(self):
        """
        Enumerate the agents in the array
        Returns:

        """
        for i, agent in enumerate(self.agents.values()):
            agent.index = i

    # ------------------------------------------------------------------------------------------------------------------
    def getMeasurements(self):
        measurements = []

        for i in range(len(self.agents)):
            agent = self.getAgentByIndex(i)
            if agent is None:
                raise ValueError(f"Agent with index {i} does not exist.")

            if len(agent.measurements) > 0:
                measurements.extend(agent.measurements)

        return measurements

    # ------------------------------------------------------------------------------------------------------------------
    def prediction(self):
        """
        Calculate the prediction of the full system
        Returns:

        """

        # Predict the states
        x_hat = np.zeros(len(self.agents) * AGENT_STATE_DIM)
        for i in range(len(self.agents)):
            agent = self.getAgentByIndex(i)
            if agent is None:
                raise ValueError(f"Agent with index {i} does not exist.")
            x_hat[i * AGENT_STATE_DIM:(i + 1) * AGENT_STATE_DIM] = self.predictionAgent(agent.state_augmented,
                                                                                        agent.input)

        # Predict the covariance

        # Calculate the dynamics jacobian
        F = self.dynamicsJacobian()

        # dynamics_noise = np.zeros_like(self.state_covariance)  # TODO
        dynamics_noise = np.eye(4 * len(self.agents))
        for i in range(len(self.agents)):
            agent = self.getAgentByIndex(i)
            dynamics_noise[i * 4:(i + 1) * 4, i * 4:(i + 1) * 4] = np.eye(4) * agent.dynamics_noise

        P_hat = F @ self.state_covariance @ F.T + dynamics_noise

        return x_hat, P_hat

    # ------------------------------------------------------------------------------------------------------------------
    def jacobianAgent(self, state: np.ndarray, input: np.ndarray):
        """
        Calculate the Jacobian matrix of the agent's motion model
        Args:
            state:
            input:

        Returns:

        """
        F = np.array([
            [1, 0, self.Ts * input[INDEX_V], 0],
            [0, 1, 0, self.Ts * input[INDEX_V]],
            [0, 0, 1, self.Ts * input[INDEX_PSIDOT]],
            [0, 0, -self.Ts * input[INDEX_PSIDOT], 1]
        ])
        return F

    # ------------------------------------------------------------------------------------------------------------------
    def dynamicsJacobian(self):
        """
        Calculate the Jacobian matrix of the full system
        Returns:

        """
        J = np.zeros((len(self.agents) * AGENT_STATE_DIM, len(self.agents) * AGENT_STATE_DIM))

        for i in range(len(self.agents)):
            agent = self.getAgentByIndex(i)
            if agent is None:
                raise ValueError(f"Agent with index {i} does not exist.")
            J[i * AGENT_STATE_DIM:(i + 1) * AGENT_STATE_DIM, i * AGENT_STATE_DIM:(i + 1) * AGENT_STATE_DIM] = \
                self.jacobianAgent(agent.state_augmented, agent.input)

        return J

    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def measurementPredictionAgent(agent_source_state_augmented, agent_target_state_augmented):
        """
        Prediction for one agent for the measurement model
        Args:
            agent_source_state:
            agent_target_state:

        Returns:

        """
        x1 = agent_source_state_augmented[INDEX_X]
        y1 = agent_source_state_augmented[INDEX_Y]
        s1 = agent_source_state_augmented[INDEX_SIN]
        c1 = agent_source_state_augmented[INDEX_COS]

        x2 = agent_target_state_augmented[INDEX_X]
        y2 = agent_target_state_augmented[INDEX_Y]
        s2 = agent_target_state_augmented[INDEX_SIN]
        c2 = agent_target_state_augmented[INDEX_COS]

        h_source_target = np.array([
            [c1 * (x2 - x1) + s1 * (y2 - y1)],
            [-s1 * (x2 - x1) + c1 * (y2 - y1)],
            [s2 * c1 - c2 * s1],
            [c2 * c1 + s2 * s1],
        ])

        return h_source_target

    # ------------------------------------------------------------------------------------------------------------------
    def calculatePredictionCovariance(self, state_covariance, dynamics_jacobian, dynamics_noise_covariance):
        return dynamics_jacobian @ state_covariance @ dynamics_jacobian.T + dynamics_noise_covariance

    # ------------------------------------------------------------------------------------------------------------------
    def measurementJacobian(self):

        H = np.zeros((3 * (len(self.agents) ** 2), 3 * len(self.agents)))

        for i in range(len(self.agents)):
            sub_H = np.zeros((3 * len(self.agents), 3 * len(self.agents)))

            for ii in range(len(self.agents)):
                for jj in range(len(self.agents)):
                    if i == ii:
                        continue

                    if jj == i:
                        H_agent = self.measurementJacobianAgents(self.getAgentByIndex(i), self.getAgentByIndex(ii), 1)
                        pass
                    elif ii == jj:
                        H_agent = self.measurementJacobianAgents(self.getAgentByIndex(i), self.getAgentByIndex(jj), 2)
                        pass
                    else:
                        continue

                    sub_H[3 * ii:3 * (ii + 1), 3 * jj:3 * (jj + 1)] = H_agent
                    pass

            H[3 * len(self.agents) * i:3 * len(self.agents) * (i + 1), :] = sub_H
        return H

    # ------------------------------------------------------------------------------------------------------------------
    def measurementJacobian_sparse(self, measurements: list[VisionAgentMeasurement]) -> np.ndarray:

        H = np.zeros((AGENT_STATE_DIM * len(measurements), AGENT_STATE_DIM * len(self.agents)))

        for i, measurement in enumerate(measurements):
            H_meas = np.zeros((AGENT_STATE_DIM, len(self.agents) * AGENT_STATE_DIM))
            index_source = measurement.source_index
            index_target = measurement.target_index
            H_source = self.measurementJacobianAgents(
                agent_source=self.getAgentByIndex(measurement.source_index),
                agent_target=self.getAgentByIndex(measurement.target_index),
                reference_agent=1
            )
            H_target = self.measurementJacobianAgents(
                agent_source=self.getAgentByIndex(measurement.source_index),
                agent_target=self.getAgentByIndex(measurement.target_index),
                reference_agent=2
            )

            H_meas[:, AGENT_STATE_DIM * index_source:AGENT_STATE_DIM * (index_source + 1)] = H_source
            H_meas[:, AGENT_STATE_DIM * index_target:AGENT_STATE_DIM * (index_target + 1)] = H_target

            H[AGENT_STATE_DIM * i:AGENT_STATE_DIM * (i + 1), :] = H_meas

        return H

    # ------------------------------------------------------------------------------------------------------------------
    def buildMeasurementCovariance_sparse(self, measurements: list[VisionAgentMeasurement]) -> np.ndarray:
        W = np.zeros((AGENT_STATE_DIM * len(measurements), AGENT_STATE_DIM * len(measurements)))

        for i, measurement in enumerate(measurements):
            W_meas = np.eye(AGENT_STATE_DIM) @ measurement.measurement_covariance_augmented
            W[i * AGENT_STATE_DIM:(i + 1) * AGENT_STATE_DIM, i * AGENT_STATE_DIM:(i + 1) * AGENT_STATE_DIM] = W_meas

        return W

    # ------------------------------------------------------------------------------------------------------------------
    def buildMeasurementVector_sparse(self, measurements: list[VisionAgentMeasurement]) -> np.ndarray:
        y = np.zeros(AGENT_STATE_DIM * len(measurements))

        for i, measurement in enumerate(measurements):
            y[i * AGENT_STATE_DIM:(i + 1) * AGENT_STATE_DIM] = measurement.measurement_augmented

        return y

    # ------------------------------------------------------------------------------------------------------------------
    def measurementPrediction_sparse(self, measurements: list[VisionAgentMeasurement]) -> np.ndarray:
        y_est = np.zeros(AGENT_STATE_DIM * len(measurements))

        for i, measurement in enumerate(measurements):
            agent_source = self.getAgentByIndex(measurement.source_index)
            agent_target = self.getAgentByIndex(measurement.target_index)

            predicted_measurement = self.measurementPredictionAgent(
                agent_source_state_augmented=agent_source.state_augmented,
                agent_target_state_augmented=agent_target.state_augmented)

            y_est[i * AGENT_STATE_DIM:(i + 1) * AGENT_STATE_DIM] = predicted_measurement.flatten()

        return y_est

    # ------------------------------------------------------------------------------------------------------------------
    def measurementJacobianAgents(self, agent_source, agent_target, reference_agent):
        assert (reference_agent in [1, 2])

        if reference_agent == 1:

            x_1 = agent_source.state[0]
            y_1 = agent_source.state[1]
            x_2 = agent_target.state[0]
            y_2 = agent_target.state[1]

            c_1 = agent_source.state_augmented[INDEX_COS]
            s_1 = agent_source.state_augmented[INDEX_SIN]

            c_2 = agent_target.state_augmented[INDEX_COS]
            s_2 = agent_target.state_augmented[INDEX_SIN]

            H = np.array([
                [-c_1, -s_1, y_2 - y_1, x_2 - x_1],
                [s_1, -c_1, -x_2 + x_1, y_2 - y_1],
                [0, 0, -c_2, s_2],
                [0, 0, s_2, c_2]
            ])

            pass

        elif reference_agent == 2:
            x_1 = agent_source.state[0]
            y_1 = agent_source.state[1]
            x_2 = agent_target.state[0]
            y_2 = agent_target.state[1]

            c_1 = agent_source.state_augmented[INDEX_COS]
            s_1 = agent_source.state_augmented[INDEX_SIN]

            c_2 = agent_target.state_augmented[INDEX_COS]
            s_2 = agent_target.state_augmented[INDEX_SIN]

            H = [
                [c_1, s_1, 0, 0],
                [-s_1, c_1, 0, 0],
                [0, 0, c_1, -s_1],
                [0, 0, s_1, c_1],
            ]

        else:
            return None
        return H

    # ------------------------------------------------------------------------------------------------------------------
    def measurementPrediction(self):

        prediction_vector = np.zeros(3 * len(self.agents) ** 2)

        for i in range(len(self.agents)):
            agent_from = self.getAgentByIndex(i)
            if agent_from is None:
                raise ValueError(f"Agent with index {i} does not exist.")
            for j in range(len(self.agents)):
                agent_to = self.getAgentByIndex(j)
                if agent_to is None:
                    raise ValueError(f"Agent with index {j} does not exist.")

                if i == j:
                    continue

                predicted_measurement = self.measurementPredictionAgent(agent_from.state, agent_to.state)
                prediction_vector[i * len(self.agents) * 3 + 3 * j:i * len(self.agents) * 3 + 3 * (
                        j + 1)] = predicted_measurement.flatten()
                pass

        return prediction_vector

    # ------------------------------------------------------------------------------------------------------------------
    def buildMeasurementVector(self):

        y = np.zeros(3 * len(self.agents) ** 2)
        for i in range(len(self.agents)):
            agent_from = self.getAgentByIndex(i)
            if agent_from is None:
                raise ValueError(f"Agent with index {i} does not exist.")

            for j in range(len(self.agents)):
                agent_to = self.getAgentByIndex(j)
                if agent_to is None:
                    raise ValueError(f"Agent with index {j} does not exist.")

                if i == j:
                    continue

                # Check if agent from has a measurement to agent_to in its measurements
                measurement_found = False
                measurement: VisionAgentMeasurement = None
                for m in agent_from.measurements:
                    if m.target_index == j:
                        measurement_found = True
                        measurement = m
                        break

                if measurement_found:

                    y[i * len(self.agents) * 3 + 3 * j:i * len(self.agents) * 3 + 3 * (j + 1)] = measurement.measurement
                else:
                    continue

        return y

    def buildMeasurementCovariance(self):

        value_measurement_exists = 1e-5
        value_measurement_not_exists = 1e9

        W = 0 * np.ones((3 * len(self.agents) ** 2, 3 * len(self.agents) ** 2))

        for i in range(len(self.agents)):
            agent_from = self.getAgentByIndex(i)
            if agent_from is None:
                raise ValueError(f"Agent with index {i} does not exist.")

            for j in range(len(self.agents)):
                agent_to = self.getAgentByIndex(j)
                if agent_to is None:
                    raise ValueError(f"Agent with index {j} does not exist.")

                offset = len(self.agents) * 3 * i

                if i == j:
                    W[offset + 3 * j:offset + 3 * (j + 1), offset + 3 * j:offset + 3 * (j + 1)] = np.eye(
                        3) * value_measurement_not_exists
                    continue

                measurement_found = False
                measurement: VisionAgentMeasurement = None
                for m in agent_from.measurements:
                    if m.target_index == j:
                        measurement_found = True
                        measurement = m
                        break

                if measurement_found:
                    W[offset + 3 * j:offset + 3 * (j + 1), offset + 3 * j:offset + 3 * (j + 1)] = np.eye(
                        3) * value_measurement_exists
                else:
                    W[offset + 3 * j:offset + 3 * (j + 1), offset + 3 * j:offset + 3 * (j + 1)] = np.eye(
                        3) * value_measurement_not_exists

        return W

    # ------------------------------------------------------------------------------------------------------------------
    def getAgentByIndex(self, index: int) -> (VisionAgent):
        for agent in self.agents.values():
            if agent.index == index:
                return agent
        return None

    # ------------------------------------------------------------------------------------------------------------------
    def getAgentIndex(self, id: str) -> (int, None):
        for i, agent in enumerate(self.agents.values()):
            if agent.id == id:
                return i
