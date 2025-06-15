from scipy.optimize import linear_sum_assignment
import numpy as np
from extensions.simulation.src.core.environment import Object
from extensions.simulation.examples.frodo.example_frodo import FRODO_TestAgent
import extensions.simulation.src.core as core
from extensions.simulation.src.core.spaces import State 
from typing import Tuple, cast
import logging


class Task(Object): 
    def __init__(self, id, position: tuple[float, float],space= core.spaces.Space2D(), is_assignable = True):
        self.space = space # quick fix TODO: FIx this, currently needed since space is referenced before officially set. 
        
        super().__init__(object_id=id, space = space)  # No specific space needed for tasks
        
        self.position = position
        self.assigned = False
        self.is_assignable = is_assignable

    @property
    def position(self) -> tuple[float, float]:
        if self.configuration is None:
            raise ValueError("Task configuration is None")

        config_dict = cast(dict, self.configuration[0])  # static type hint for linter

        return (float(config_dict['x']), float(config_dict['y']))
    
    @position.setter
    def position(self, pos: tuple[float, float]) -> None:

        config_dict = cast(dict, self.configuration[0])  # static type hint for linter
        config_dict['x'] = pos[0]
        config_dict['y'] = pos[1]

        self.configuration = pos

class FrodoAssignmentAgent(FRODO_TestAgent):
    def __init__(self, Ts, agent_id, is_task_agent=True):
        super().__init__(agent_id=agent_id, Ts=Ts)
        self.is_task_agent = is_task_agent  # flag to indicate if the agent is a task assignment agent
        self.available_tasks = []
        self.assigned_tasks = [] # TODO: remove this attribute if not needed
        # TODO: Use metric, e.g. dubins distance which accounts for turning radius
        self.cost_function = self.euclidean_distance_cost  # set the cost function

    @property
    def position(self) -> tuple[float, float]:
        if self.configuration is None:
            raise ValueError("Task configuration is None")

        config_dict = cast(dict, self.configuration[0])  # static type hint for linter

        return (float(config_dict['x']), float(config_dict['y']))
    
    @position.setter
    def position(self, pos: tuple[float, float]) -> None:
        state = cast(State, self.state)  # static type hint for linter
        
        config_dict = cast(dict, state[0])  # static type hint for linter
        config_dict['x'] = pos[0]
        config_dict['y'] = pos[1]

    @property
    def cost_vector(self):
        return self.compute_cost_vector()

    def calc_task_cost(self, task_configuration: State) -> np.floating:
         
        return self.cost_function(task_configuration=task_configuration)
    
    def euclidean_distance_cost(self, task_configuration: State) -> np.floating:
        if self.configuration is None or task_configuration is None:
            raise ValueError("Configuration or task_configuration is None.")
        
        # Extract position from agent and task configurations
        agent_pos = self.configuration[0]
        task_pos = task_configuration[0]

        agent_pos = cast(dict, agent_pos)  # static type hint for linter
        task_pos = cast(dict, task_pos)

        agent_xy = np.array([agent_pos[0], agent_pos[1]], dtype=float)
        task_xy = np.array([task_pos['x'], task_pos['y']], dtype=float)

        return np.linalg.norm(agent_xy - task_xy)
    
    def add_tasks(self, tasks: tuple[Task,...]) -> None:
        # Add only tasks with unique IDs to the available_tasks list
        existing_ids = {task.id for task in self.available_tasks}
        new_tasks = [task for task in tasks if task.id not in existing_ids]
        self.available_tasks += new_tasks

    def compute_cost_vector(self) -> list[np.floating]:
        if not self.available_tasks:
            logging.warning(f"Agent {self.agent_id} has no available tasks to compute cost vector.")
            return []
        task_configurations = self.extract_task_configurations(self.available_tasks)
        cost_vector = [self.calc_task_cost(task_configuration=configuration) for configuration in task_configurations]
        return cost_vector

    def extract_task_configurations(self, tasks: list[Task]) -> list[State]:
        """
        Extracts the local positions of agents or tasks from a list of objects.
        """
        configurations = []
        for task in tasks:
            configurations.append(task.configuration)
        return configurations
    
    def assign_task(self, task: Task)-> None:
        self.assigned_tasks.append(task)
    
if __name__ == "__main__":
    # Example usage
    agent = FrodoAssignmentAgent(Ts=0.1, agent_id= "assignment_agent1")
    task1 = Task(id="task1", position=(1.0, 2.0))
    task2 = Task(id="task2", position=(-1.0, 5.0))
    agent.position = (4.0, 1.0)
    agent.add_tasks((task1, task2))
    cost_vector = agent.compute_cost_vector()
    print(f"Cost vector for available tasks: {cost_vector}")
    print("agent position: ", agent.position)
    print('ids: ', task1.id, ' agent id: ', agent.agent_id)
