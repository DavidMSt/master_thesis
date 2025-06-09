from scipy.optimize import linear_sum_assignment
import numpy as np
from extensions.simulation.src.core.environment import BASE_ENVIRONMENT_ACTIONS, Object
from extensions.simulation.examples.frodo.example_frodo import FrodoEnvironment, FRODO_TestAgent
from enum import Enum, auto
import extensions.simulation.src.core as core


# TODO: Create individual files for the classes and functions

# agent.py
class TaskAssignmentAgent:
    def __init__(self,robot_interface, Ts, id = None):
        self.robot = robot_interface(agent_id = "frodo1v", Ts=Ts) # make the robot interface modular to be able to switch between different robots
        self.id = self.robot.agent_id
        self.assigned_tasks = []
        self.cost_function = self.euclidean_distance_cost # set the cost function

    @property
    def position(self):
        return self.robot.getPosition
    
    @position.setter
    def position(self, pos: tuple[float, float]):
        self.robot.setPosition = pos

    def calc_task_cost(self, task_location: tuple[float, float]) -> np.floating:
         
        return self.cost_function(task_location=task_location)
    
    def euclidean_distance_cost(self, task_location):
        # calculate the euclidean distance to the task location
        agent_pos = self.position
        return np.linalg.norm(np.array(agent_pos) - np.array(task_location))


# TODO: hat Dustin hier collision momentan rausgenommen? dort wird scioi_py_core.objects.Object genutzt
class Task(Object): # TODO: Is this the appropiate base class? Do i manually have to make this non-collidable?
    def __init__(self, id, position: tuple[float, float],space= core.spaces.Space2D()):
        self.space = space # quick fix 
        super().__init__(object_id=id, space = space)  # No specific space needed for tasks
        self.position = position
        self.assigned = False

    @property
    def position(self):
        return self.configuration
    
    @position.setter
    def position(self, pos: tuple[float, float]):
        self.configuration = pos

class AssignmentMethod(Enum):
    HUNGARIAN = auto()  # renamed from HUNGARIAN
    RANDOM = auto()     # renamed from RANDOM
    CBBA = auto()      # renamed from CBBA
    GNN = auto()       # renamed from GNN

class AssignmentManager:
    """
    _summary_ class to manage task assignments for agents in a task environment.
    It provides methods for centralized and decentralized task assignment using various algorithms.

    """

    def assign_tasks(self, agents: list[TaskAssignmentAgent], tasks: list[Task], method: AssignmentMethod):
        if method == AssignmentMethod.HUNGARIAN:
            return self.centralized_hungarian(agents, tasks)
        elif method == AssignmentMethod.RANDOM:
            return self.random_assignment(agents, tasks)
        elif method == AssignmentMethod.CBBA:
            return self.decentralized_cbba(agents, tasks)
        elif method == AssignmentMethod.GNN:
            return self.gnn_based_assignment(agents, tasks)
        else:
            raise NotImplementedError(f"Unknown assignment method: {method}")

    @staticmethod
    def centralized_hungarian(agents, tasks):
        ...

    @staticmethod
    def random_assignment(agents, tasks):
        ...

    @staticmethod   
    def decentralized_cbba(agents, tasks):
        ...

    @staticmethod
    def gnn_based_assignment(agents, tasks):
        ...

# environment.py
class TaskEnvironment(FrodoEnvironment):
    def __init__(self, x_lim, y_lim, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x_lim = x_lim # set the x limits of the environment (currently only for sampling purposes) TODO: can i use exsiting environment methods?
        self.y_lim = y_lim
        self.assingment_manager = AssignmentManager() # create an instance of the assignment manager to handle task assignments

    def spawn_agents(self, n: int, positions:list[tuple[float, float]] | None = None):
        if positions is None:
            # randomly spawn n agents within the environment limits
            for agent in range(n):
                x = np.random.uniform(0, self.x_lim)
                y = np.random.uniform(0, self.y_lim)
                new_agent = TaskAssignmentAgent(robot_interface=FRODO_TestAgent, Ts=self.Ts)
                new_agent.position = (x, y)
                self.addObject(new_agent.robot)
        else:
            for i, pos in enumerate(positions):
                new_agent = TaskAssignmentAgent(robot_interface=FRODO_TestAgent, Ts=self.Ts)
                new_agent.position = pos
                self.addObject(new_agent.robot)

    def spawn_tasks(self, n: int, positions:list[tuple[float, float]] | None = None):
        if positions is None:
            # randomly spawn n tasks within the environment limits
            for task in range(n):
                x = np.random.uniform(0, self.x_lim)
                y = np.random.uniform(0, self.y_lim)
                new_task = Task(id=f'task_{task}', location=(x, y))
                self.addObject(new_task)
        else:
            for i, pos in enumerate(positions):
                new_task = Task(id=f'task_{i}', location=pos)
                self.addObject(new_task)

    def get_agents(self):
        """_summary_
        Get all agents in the environment
        """
        return self.getObjectsByID(id='FRODO', regex=True)

    def create_groundtruth_samples(self):
        """_summary_
        Create ground truth samples that can be used for training the GNN
        """
        ... 

def main():
    env = TaskEnvironment(x_lim= 3.0, y_lim=3.0, Ts=0.1, run_mode='rt') # create the environment for the agents
    env.spawn_agents(n=5)
    env.spawn_tasks(n=5)
    print(env.getObjectsByID(id='FRODO', regex=True))  # get the agent with the ID 'frodo1v'
    # print(env.getSample())

    # env.init()
    # env.start(thread=True)

    


if __name__ == "__main__":
    main()