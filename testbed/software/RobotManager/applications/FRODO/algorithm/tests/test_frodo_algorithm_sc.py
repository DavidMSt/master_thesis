import math
import time

import numpy as np

from applications.FRODO.simulation.frodo_simulation import FRODO_Simulation, FRODO_ENVIRONMENT_ACTIONS
from applications.FRODO.algorithm.centralized_ekf_sincos import CentralizedLocationAlgorithm, VisionAgent, \
    VisionAgentMeasurement


class FRODO_Algorithm_Simulated_SC:
    simulation: FRODO_Simulation
    algorithm: CentralizedLocationAlgorithm

    def __init__(self):
        self.simulation = FRODO_Simulation()
        self.simulation.env.scheduling.actions[FRODO_ENVIRONMENT_ACTIONS.ESTIMATION].addAction(self.estimation)
        self.algorithm = CentralizedLocationAlgorithm(Ts=self.simulation.env.scheduling.Ts)

    def init(self, agents: dict[str, dict]):
        self.simulation.init()

        vision_agents_algorithm = {}
        index = 0

        for name, agent_data in agents.items():
            agent = self.simulation.addVirtualAgent(id=name, fov_deg=agent_data["fov_deg"],
                                                    view_range=agent_data["view_range"])
            agent.setPosition(agent_data["position"])
            agent.setConfiguration(dimension='psi', value=agent_data["psi"])

            vision_agents_algorithm[name] = VisionAgent(
                id=name,
                index=index,
                state=np.array([agent.state['pos']['x'], agent.state['pos']['y'],
                                agent.state['psi'].value]) if agent_data['leader'] else np.array(
                    agent_data['initial_guess']),
                state_covariance=np.diag(np.asarray(agent_data['uncertainty'])),
                input=np.array([0, 0]),
                input_covariance=np.eye(2) * 0,
                measurements=[],
                dynamics_noise=agent_data['dynamics_uncertainty']
            )
            index += 1

        self.algorithm.init(vision_agents_algorithm)

    def start(self, *args, **kwargs):
        self.simulation.start(*args, **kwargs)

    def estimation(self):
        for name, agent in self.simulation.agents.items():
            self.algorithm.agents[name].measurements = []

            noise_std = 1e-2
            for _, data in agent.measurements.items():
                algorithm_measurement = VisionAgentMeasurement(
                    source=name,
                    source_index=self.algorithm.getAgentIndex(name),
                    target=data.agent_id,
                    target_index=self.algorithm.getAgentIndex(data.agent_id),
                    measurement=np.array([data.vec[0], data.vec[1], data.psi]) + np.random.normal(0, noise_std, 3),
                    measurement_covariance=np.eye(3) * noise_std
                )

                # print(f"{name}->{data.agent_id}: {algorithm_measurement}")
                self.algorithm.agents[name].measurements.append(algorithm_measurement)


        self.algorithm.update()


def main():
    agents = {
        'frodo1_v': {
            'fov_deg': 180,
            'view_range': 2,
            'position': [0.0, 0.0],
            'initial_guess': [0.0, 0.0, 0.0],
            'psi': 0,
            'uncertainty': [1e-10, 1e-10, 1e-10],
            'dynamics_uncertainty': 1e-15,
            'leader': True
        },
        'frodo2_v': {
            'fov_deg': 10,
            'view_range': 2,
            'position': [-0.5, 1],
            'initial_guess': [0.0, 0.01, 0.0],
            'psi': 0,
            'uncertainty': [1e-2, 1e-2, 1e-2],
            'dynamics_uncertainty': 1e-2,
            'leader': False
        },
        'frodo3_v': {
            'fov_deg': 30,
            'view_range': 4,
            'position': [0.0, 1],
            # 'initial_guess': [0, 0, 2],
            'initial_guess': [0.0,0.0,0.0],
            'psi': -math.pi/2+0.01,
            'uncertainty': [1e3, 1e3, 1e4],
            'dynamics_uncertainty': 1e-2,
            'leader': False
        }
    }
    app = FRODO_Algorithm_Simulated_SC()
    app.init(agents)
    app.start()

    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
