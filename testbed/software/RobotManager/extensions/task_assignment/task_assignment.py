from scipy.optimize import linear_sum_assignment
import numpy as np
from extensions.simulation.src.core.environment import BASE_ENVIRONMENT_ACTIONS
from extensions.simulation.examples.frodo.example_frodo import FrodoEnvironment, FRODO_TestAgent


# TODO: Create individual files for the classes and functions

# agent.py
class TaskAssignmentAgent:
    # TODO: also set the ID and TS
    def __init__(self,robot_interface, Ts, id = None):
        self.robot = robot_interface(agent_id = "frodo1v", Ts=Ts) # make the robot interface modular to be able to switch between different robots
        self.id = self.robot.agent_id
        self.assigned_tasks = []

    @property
    def position(self):
        return self.robot.getPosition
    
    @position.setter
    def set_position(self, pos: tuple[float, float]):
        self.robot.setPosition = pos

# task.py
class Task: # TODO: find appropiate base class
    def __init__(self, id, location):
        self.id = id
        self.location = location
        self.assigned = False

# environment.py
class TaskEnvironment(FrodoEnvironment):
    def __init__(self, x_lim, y_lim, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x_lim = x_lim
        self.y_lim = y_lim

    def spawn_agents(self, n: int, positions:list[tuple[float, float]] | None = None):
        if positions is None:
            # randomly spawn n agents within the environment limits
            for agent in range(n):
                x = np.random.uniform(0, self.x_lim)
                y = np.random.uniform(0, self.y_lim)
                new_agent = TaskAssignmentAgent(robot_interface=FRODO_TestAgent, Ts=self.Ts)
                new_agent.set_position = (x, y)
                self.addObject(new_agent.robot)
        else:
            for i, pos in enumerate(positions):
                new_agent = TaskAssignmentAgent(robot_interface=FRODO_TestAgent, Ts=self.Ts)
                new_agent.set_position = pos
                self.addObject(new_agent.robot)

    # Todo: How do I get the agents positions from inside the environment?

    def spawn_tasks(self, n):
        # create n tasks
        ...

class AssignmentManager:
    def __init__(self, cost_function, method="hungarian"):
        ...

    def compute_cost_matrix(self, agents, tasks):
        ...

    def assign_tasks(self, agents, tasks):
        ...


def main():
    env = TaskEnvironment(x_lim= 3.0, y_lim=3.0, Ts=0.1, run_mode='rt') # create the environment for the agents
    env.spawn_agents(n=3)
    print(env.getObjectsByID(id='FRODO', regex=True))  # get the agent with the ID 'frodo1v'
    # print(env.getSample())

    # env.init()
    # env.start(thread=True)

    


if __name__ == "__main__":
    main()