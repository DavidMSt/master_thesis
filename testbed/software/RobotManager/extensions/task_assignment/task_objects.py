from scipy.optimize import linear_sum_assignment
import numpy as np
from extensions.simulation.src.core.environment import BASE_ENVIRONMENT_ACTIONS, Object
from extensions.simulation.examples.frodo.example_frodo import FrodoEnvironment, FRODO_TestAgent
from enum import Enum, auto
import extensions.simulation.src.core as core

class TaskAssignmentAgent:
    def __init__(self,robot_interface, Ts, id = None, is_task_agent = True):
        self.robot = robot_interface(agent_id = "frodo1v", Ts=Ts) # make the robot interface modular to be able to switch between different robots
        self.id = self.robot.agent_id
        self.is_task_agent = is_task_agent # flag to indicate if the agent is a task assignment agent
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
    def __init__(self, id, position: tuple[float, float],space= core.spaces.Space2D(), is_assignable = True):
        self.space = space # quick fix 
        super().__init__(object_id=id, space = space)  # No specific space needed for tasks
        self.position = position
        self.assigned = False
        self.is_assignable = is_assignable

    @property
    def position(self):
        return self.configuration
    
    @position.setter
    def position(self, pos: tuple[float, float]):
        self.configuration = pos