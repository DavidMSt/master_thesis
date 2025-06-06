# assignment_manager.py
from scipy.optimize import linear_sum_assignment
from ../simulation
import numpy as np

# agent.py
class Agent:
    def __init__(self, id, position):
        self.id = id
        self.position = position
        self.assigned_tasks = []

# task.py
class Task:
    def __init__(self, id, location):
        self.id = id
        self.location = location
        self.assigned = False

# environment.py
class Environment:
    def __init__(self, x_lim, y_lim, obstacles=None):
        self.x_lim = x_lim
        self.y_lim = y_lim
        self.obstacles = obstacles if obstacles else []

    def is_valid_position(self, pos):
        # implement bound & obstacle check
        ...

    def spawn_agents(self, n):
        # create n agents at random or predefined positions
        ...

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

if __name__ == "__main__":
    print(np.array([1,2,3]))