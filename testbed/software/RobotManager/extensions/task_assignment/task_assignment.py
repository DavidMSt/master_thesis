from scipy.optimize import linear_sum_assignment
import numpy as np
from extensions.simulation.src.core.environment import BASE_ENVIRONMENT_ACTIONS, Object
from extensions.simulation.examples.frodo.example_frodo import FrodoEnvironment, FRODO_TestAgent
from enum import Enum, auto
import extensions.simulation.src.core as core
from task_objects import Task, TaskAssignmentAgent
from numpy.typing import NDArray


# TODO: Create individual files for the classes and functions
class AssignmentMethod(Enum):
    HUNGARIAN = auto()  
    RANDOM = auto()     
    CBBA = auto()      
    GNN = auto()       

class AssignmentManager:
    
    def __init__(self):
        self.assignment_matrix: NDArray[np.bool] | None = None
        self.cost_matrix: NDArray[np.float64] | None = None

    def create_assignment(self, agents: list[TaskAssignmentAgent], tasks: list[Task], method: AssignmentMethod):
        
        # Validate that agents and tasks are non-empty
        if not agents:
            raise ValueError("The agents list is empty. At least one agent is required for task assignment.")
        if not tasks:
            raise ValueError("The tasks list is empty. At least one task is required for assignment.")
        
    
        for agent in agents:
            agent.add_tasks(tasks) # add available tasks to agents
            agent.compute_cost_vector() # compute cost vector for all tasks

        # # Select the assignment method
        # if method == AssignmentMethod.HUNGARIAN:
        #     return self.centralized_hungarian(agents)
        # elif method == AssignmentMethod.RANDOM:
        #     return self.random_assignment(agents)
        # elif method == AssignmentMethod.CBBA:
        #     return self.decentralized_cbba(agents)
        # elif method == AssignmentMethod.GNN:
        #     return self.gnn_based_assignment(agents)
        # else:
        #     raise NotImplementedError(f"Unknown assignment method: {method}. Available methods are: {[m.name for m in AssignmentMethod]}")

    @staticmethod
    def centralized_hungarian(agents):
        ...

    @staticmethod
    def random_assignment(agents):
        ...

    @staticmethod   
    def decentralized_cbba(agents):
        ...

    @staticmethod
    def gnn_based_assignment(agents):
        ...

    def send_assignment(self, agent: TaskAssignmentAgent, task: Task):
        # Give agent centralized computed assignment
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
                new_task = Task(id=f'task_{task}', position=(x, y))
                self.addObject(new_task)
                print(f"Spawned task {new_task.id} at position {new_task.position}")
        else:
            # spawn tasks at specified positions
            if len(positions) != n:
                raise ValueError("Number of positions don't equal number of tasks.")
            for i, pos in enumerate(positions):
                new_task = Task(id=f'task_{i}', position=pos)
                self.addObject(new_task)

    def get_assignment_agents(self) -> list:
        agents = self.getObjectsByID(id="FRODO", regex=True)
        task_agents = [a for a in agents if getattr(a, 'is_task_agent', False)]

        return task_agents if task_agents else []


    def get_assignment_tasks(self) -> list:
        tasks = self.getObjectsByID(id = "Task", regex=True)
        task_assignable = [a for a in tasks if getattr(a, 'is_assignable', False)]

        return task_assignable if task_assignable else []

    def create_assignments(self, method: AssignmentMethod = AssignmentMethod.HUNGARIAN):
        self.assingment_manager.create_assignment(
            agents=self.get_assignment_agents(),
            tasks=self.get_assignment_tasks(),
            method=method
        )

    def create_groundtruth_samples(self):
        """_summary_
        Create ground truth samples that can be used for training the GNN
        """
        ... 

def main():
    env = TaskEnvironment(x_lim= 3.0, y_lim=3.0, Ts=0.1, run_mode='rt') # create the environment for the agents
    env.spawn_agents(n=3)
    env.spawn_tasks(n=5)
    # print(env.get_assignment_agents())
    print(type(env.get_assignment_tasks()))
    env.get_assignment_agents()
    #print(env.getObjectsByID(id='FRODO', regex=True))  # get the agent with the ID 'frodo1v'
    
    # print(env.getSample())

    # env.init()
    # env.start(thread=True)

    


if __name__ == "__main__":
    main()