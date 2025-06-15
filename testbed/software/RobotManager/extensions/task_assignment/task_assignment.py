from scipy.optimize import linear_sum_assignment
import numpy as np
from extensions.simulation.src.core.environment import BASE_ENVIRONMENT_ACTIONS, Object
from extensions.simulation.examples.frodo.example_frodo import FrodoEnvironment
from enum import Enum, auto
import extensions.simulation.src.core as core
from task_objects import Task, FrodoAssignmentAgent
from numpy.typing import NDArray

class AssignmentMethod(Enum):
    HUNGARIAN = auto()  
    RANDOM = auto()     
    CBBA = auto()      
    GNN = auto()       

class AssignmentManager:
    
    # def __init__(self, tasks: tuple[Task,...], agents: tuple[FrodoAssignmentAgent,...]):
    def __init__(self, objects: dict[str, Object]):
        self._objects = objects
        # self._agents = agents # reference agents and tasks from environment
        # self._tasks = tasks
        # self.assignment_matrix: NDArray[np.bool] | None = None
        # self.cost_matrix: NDArray[np.float64] | None = None

    @property # no setter needed, only read access
    def agents(self) -> tuple[FrodoAssignmentAgent, ...]:
        return tuple(obj for obj in self._objects.values() if isinstance(obj, FrodoAssignmentAgent))

    @property # no setter needed, only read access
    def tasks(self) -> tuple[Task, ...]:
        return tuple(obj for obj in self._objects.values() if isinstance(obj, Task))

    def create_assignment(self, selected_agents: tuple[FrodoAssignmentAgent, ...]| None =None, selected_tasks: tuple[Task, ...]| None = None, selected_method: AssignmentMethod = AssignmentMethod.HUNGARIAN) -> NDArray[np.bool]:
        # if none specified
        if selected_agents is None:
            selected_agents = self.agents
        if selected_tasks is None:
            selected_tasks = self.tasks
        
        # Validate that agents and tasks are non-empty
        if not selected_agents:
            raise ValueError("The agents list is empty. At least one agent is required for task assignment.")
        if not selected_tasks:
            raise ValueError("The tasks list is empty. At least one task is required for assignment.")
        
        self.send_tasks_to_agents(self.tasks)  # send all tasks to all agents before assignment

        # Select the assignment method
        if selected_method == AssignmentMethod.HUNGARIAN:
            return self.centralized_hungarian(agents=selected_agents, tasks=selected_tasks)
        elif selected_method == AssignmentMethod.RANDOM:
            return self.random_assignment(selected_agents)
        elif selected_method == AssignmentMethod.CBBA:
            return self.decentralized_cbba(selected_agents)
        elif selected_method == AssignmentMethod.GNN:
            return self.gnn_based_assignment(selected_agents)
        else:
            raise NotImplementedError(f"Unknown assignment method: {selected_method}. Available methods are: {[m.name for m in AssignmentMethod]}")
    
    def send_tasks_to_agents(self, tasks: tuple[Task, ...],  selected_agents: tuple[FrodoAssignmentAgent, ...]| None = None)-> None:
        """Send tasks to agents based on the assignment matrix."""
        if selected_agents is None:
            selected_agents = self.agents # All agents are selected if none are specified

        for _, agent in enumerate(selected_agents):
            agent.add_tasks(tasks) # add available tasks to agents

    @property
    def cost_matrix(self) -> NDArray[np.float64] | None:
        cost_matrix = np.zeros((len(self.agents), len(self.tasks)), dtype=np.float64)

        for i, agent in enumerate(self.agents):
        
            cost_vector_i = agent.cost_vector # get vector for all tasks available to the agent #TODO: Not suited for case of unavailable tasks
            cost_matrix[i, :] = cost_vector_i

        return cost_matrix

    def centralized_hungarian(self, agents: tuple[FrodoAssignmentAgent, ...], tasks: tuple[Task, ...]) -> NDArray[np.bool]:
        assignment_matrix = np.zeros((len(agents), len(tasks)), dtype=bool)
        cost_matrix = self.cost_matrix
        print("this is the cost matrix", cost_matrix)
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        assignment_matrix[row_ind, col_ind] = True
        assignment_matrix = assignment_matrix.astype(bool)
        assignment_matrix = assignment_matrix.astype(np.bool_)
        print(assignment_matrix)
        return assignment_matrix
        

    @staticmethod
    def random_assignment(agents):
        raise NotImplementedError("Random assignment method is not implemented yet.")

    @staticmethod   
    def decentralized_cbba(agents):
        raise NotImplementedError("Decentralized CBBA method is not implemented yet.")

    @staticmethod
    def gnn_based_assignment(agents):
        raise NotImplementedError("GNN-based assignment method is not implemented yet.")

    def send_assignment(self, agent: FrodoAssignmentAgent, task: Task):
        # Give agent centralized computed assignment
        agent.assign_task(task)

# environment.py
class TaskEnvironment(FrodoEnvironment):
    def __init__(self, x_lim, y_lim, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x_lim = x_lim # set the x limits of the environment (currently only for sampling purposes) TODO: can i use exsiting environment methods?
        self.y_lim = y_lim
        self.agents_list = [] # list to store agents TODO: Remove this and get the information from the environment 
        self.tasks_list = [] # list to store tasks
        self.assingment_manager = AssignmentManager(objects=self.objects) # create an instance of the assignment manager to handle task assignments

    @property
    def _agents(self) -> tuple[FrodoAssignmentAgent, ...]:
        return tuple(self.get_assignment_agents())
    
    @property
    def _tasks(self) -> tuple[Task, ...]:
        return tuple(self.get_assignment_tasks())

    def spawn_agents(self, n: int, positions:list[tuple[float, float]] | None = None):
        if positions is None:
            # randomly spawn n agents within the environment limits
            for n, i in enumerate(range(n)):
                x = np.random.uniform(0, self.x_lim)
                y = np.random.uniform(0, self.y_lim)
                new_agent = FrodoAssignmentAgent(Ts=self.Ts, agent_id=f'agent_{n}')
                new_agent.position = (x, y) # TODO: sample here also orientation once distance function can handle it
                self.addObject(new_agent)
        else:
            for i, pos in enumerate(positions):
                new_agent = FrodoAssignmentAgent(Ts=self.Ts, agent_id=f'agent_{i}')
                new_agent.position = pos
                self.addObject(new_agent)

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

    def assign_tasks(self):
        """Assign tasks to agents using the assignment manager."""
        agents = self.get_assignment_agents()
        tasks = self.get_assignment_tasks()
        if not agents or not tasks:
            raise ValueError("No agents or tasks available for assignment.")
        self.assingment_manager.create_assignment(selected_agents=agents, selected_tasks=tasks, selected_method=AssignmentMethod.HUNGARIAN)

    ##### Get assignment objects #####

    def get_assignment_agents(self) -> list[FrodoAssignmentAgent]:
        return [obj for obj in self.objects.values() if isinstance(obj, FrodoAssignmentAgent)]

    def get_assignment_tasks(self) -> list[Task]:
        return [obj for obj in self.objects.values() if isinstance(obj, Task)]
    
    ##### Get positions of agents and tasks - not used for computation #####

    def get_agent_positions(self) -> list[tuple[float, float]]:
        """Get the positions of all agents in the environment."""
        agents = self.get_assignment_agents()
        return [agent.position for agent in agents]
    
    def get_task_positions(self) -> list[tuple[float, float]]:
        """Get the positions of all tasks in the environment."""
        tasks = self.get_assignment_tasks()
        return [task.position for task in tasks]

    def create_groundtruth_samples(self):
        """_summary_
        Create ground truth samples that can be used for training the GNN
        """
        ... 


if __name__ == "__main__":
    env = TaskEnvironment(x_lim= 3.0, y_lim=3.0, Ts=0.1, run_mode='rt') # create the environment for the agents
    env.spawn_agents(n=5)
    env.spawn_tasks(n=5)
    env.assign_tasks()  # Assign tasks to agents using the assignment manager

    