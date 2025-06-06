"""
Action and Scheduling Classes – Tutorial and Reference
========================================================

This module defines the core classes for scheduling and executing actions within the simulation.
An Action is a wrapper around a callable that can be scheduled by a Scheduler. Actions may have child
actions, default parameters, lambda expressions to compute dynamic parameters, and a priority.

Tutorial
--------
1. Creating an Action:
   To create an action, instantiate the Action class by providing:
     - action_id (a unique identifier string). If not provided, it is autogenerated from the function name.
     - function: the callable to be executed.
     - parameters: (optional) a dictionary of default arguments.
     - lambdas: (optional) a dictionary of lambda functions that are evaluated at call time.
     - frequency: (optional) how often the action should be executed (default is every call).
     - priority: (optional) an integer that sets the order among sibling actions (lower value = higher priority).

   Example:
       def my_function(x, y):
           return x + y
       action = Action(action_id="add_action", function=my_function,
                       parameters={"x": 2}, lambdas={"y": lambda: 3}, priority=5)

2. Adding Child Actions:
   To add a child action to an existing action, simply call the parent action’s
   `addAction(child_action)` method. The child action’s parent list is updated accordingly,
   and child actions are sorted by priority.

   Example:
       child_action = Action(action_id="child", function=lambda: print("Child action"), priority=10)
       action.addAction(child_action)
       # Alternatively, you can also add a parent to an action:
       child_action.addParent(action)

3. Running Actions:
   Calling an Action instance (or using its `run()` method) will execute its stored function,
   passing in a merge of default parameters, any extra arguments, and the results of the lambda expressions.
   It will then iterate through and call any registered child actions.

4. Scheduler Integration:
   The Scheduler uses the top-level Action (or a group of Actions) to step through the simulation.
   See the Scheduler class for details on starting the simulation, using SimPy events, and running in
   either real-time or fast mode.

---------------------------------------------------------------------

Below is the complete source code for the Action and Scheduling classes.
"""

import dataclasses
import enum
import threading
import time
from abc import ABC, abstractmethod
from typing import Union, List, Callable, Dict
import simpy


class Action:
    """
    An Action is a wrapper around a callable that gets executed within a specific phase by the Scheduler.

    Attributes:
        id (str): A unique identifier for this action.
        function (callable): The function to be executed.
        parameters (dict): Default arguments for the function.
        lambdas (dict): Dictionary of lambda functions to be evaluated at call time.
        object (ScheduledObject): The scheduled object this action is associated with.
        frequency (int): How often (in ticks) this action should be executed.
        priority (int): Priority for sorting among sibling actions (lower value means higher priority).
        actions (dict[str, Action]): Child actions.
        _parents (list[Action]): List of parent actions.
    """

    function: Callable
    parameters: Dict
    lambdas: Dict
    object: 'ScheduledObject'
    frequency: int
    priority: int
    actions: Dict[str, 'Action']
    id: str

    def __init__(self, action_id: str = None, function: Callable = None,
                 parent: Union['Action', List['Action']] = None,
                 parameters: dict = None, lambdas: dict = None,
                 object: 'ScheduledObject' = None,
                 frequency: int = 1, priority: int = 1):
        """
        Initialize an Action.

        Args:
            action_id (str, optional): Unique identifier for the action. If None, it is autogenerated.
            function (callable, optional): The callable to execute.
            parent (Action or list[Action], optional): Parent action(s).
            parameters (dict, optional): Default parameters for the function.
            lambdas (dict, optional): Lambdas to evaluate at call time.
            object (ScheduledObject, optional): The object to register this action with.
            frequency (int): Frequency of execution.
            priority (int): Priority for sorting.
        """
        if parameters is None:
            parameters = {}
        if lambdas is None:
            lambdas = {}

        self.actions = {}
        self.parameters = parameters
        self.lambdas = lambdas
        self.function = function
        self.frequency = frequency
        self.priority = priority

        # Generate a unique identifier if not provided.
        if action_id is None:
            if function is not None:
                action_id = f"{function.__name__}_{id(self)}"
            else:
                action_id = f"{id(self)}"
        self.id = action_id

        self._parents: List[Action] = []  # Allow multiple parents

        # If a parent is provided, add it/them.
        if parent is not None:
            if isinstance(parent, list):
                for p in parent:
                    self.addParent(p)
            else:
                self.addParent(parent)

        # Register with the object if provided.
        if object is not None:
            object.addAction(self)

    @property
    def parents(self) -> List['Action']:
        """Return the list of parent actions."""
        return self._parents

    @property
    def parent(self) -> Union['Action', None]:
        """
        For backward compatibility, return the first parent if available.
        Note: An action may have multiple parents.
        """
        return self._parents[0] if self._parents else None

    def addParent(self, parent: 'Action'):
        """
        Add a parent action to this Action.

        Args:
            parent (Action): The parent action to add.
        """
        if parent not in self._parents:
            self._parents.append(parent)
            # Ensure self is registered as a child of the parent.
            if self not in parent.actions.values():
                parent.addAction(self)

    def removeParent(self, parent: 'Action'):
        """
        Remove a parent action from this Action.

        Args:
            parent (Action): The parent action to remove.
        """
        if parent in self._parents:
            self._parents.remove(parent)

    def run(self, *args, **kwargs):
        """
        Execute the action. Evaluates lambda parameters and then calls the function with a merged set
        of arguments (default parameters, additional kwargs, and lambda outputs). Then runs all child actions.
        """
        # If 'calltree' is provided for debugging, print the call trace.
        if kwargs.get('calltree', False):
            try:
                print(
                    f"Action: \"{self.id}\" Object: \"{self.object.id if self.object else 'None'}\": {type(self.object).__name__}")
            except AttributeError:
                print(f"Action: \"{self.id}\" Object: None")
        # Evaluate lambda expressions.
        lambdas_exec = {key: value() for key, value in self.lambdas.items()}
        # Execute the main function.
        if self.function is not None:
            ret = self.function(*args, **{**self.parameters, **kwargs, **lambdas_exec})
        # Execute child actions.
        for child in self.actions.values():
            child(*args, **{**self.parameters, **kwargs, **lambdas_exec})

    def addAction(self, action: Union['Action', List['Action'], Callable]):
        """
        Register a child action or list of child actions.

        Args:
            action (Action or list[Action] or callable): Action(s) to be registered as a child.
        """
        if isinstance(action, list):
            for ac in action:
                if not isinstance(ac, Action):
                    raise AssertionError("All items must be Action instances.")
                self.addAction(ac)
        elif isinstance(action, Action):
            # Add self as a parent to the child action if not already present.
            if self not in action._parents:
                action._parents.append(self)
            # Use the action's id as key. If an action with the same id exists, append a unique identifier.
            key = action.id
            if key in self.actions:
                key = f"{key}_{id(action)}"
            self.actions[key] = action
            # Sort child actions by priority.
            self.actions = dict(sorted(self.actions.items(), key=lambda item: item[1].priority))
        elif callable(action):
            self.addAction(Action(action_id=None, function=action))
        else:
            raise TypeError("addAction accepts an Action instance, a list of Actions, or a callable.")

    def removeAction(self, action: Union['Action', List['Action']]):
        """
        Remove a child action or list of child actions.

        Args:
            action (Action or list[Action]): Action(s) to remove.
        """
        if isinstance(action, list):
            for ac in action:
                self.removeAction(ac)
        elif isinstance(action, Action):
            # Remove the action from this parent's actions dictionary.
            keys_to_remove = [key for key, act in self.actions.items() if act is action]
            for key in keys_to_remove:
                del self.actions[key]
            # Remove this parent from the child's parent list.
            action.removeParent(self)
            # Re-sort the dictionary.
            self.actions = dict(sorted(self.actions.items(), key=lambda item: item[1].priority))

    def removeAllActions(self):
        self.actions = {}

    def __call__(self, *args, **kwargs):
        """Allow the Action instance to be called directly to execute it."""
        return self.run(*args, **kwargs)


@dataclasses.dataclass
class SchedulingData:
    """
    Contains scheduling data for a ScheduledObject.

    Attributes:
        _object (ScheduledObject): The associated scheduled object.
        _parent (ScheduledObject): Parent object.
        tick (int): Internal tick counter.
        _t (float): Internal time.
        _Ts (float): Sample time.
        children (list[ScheduledObject]): List of child scheduled objects.
        events (dict): Registered events.
        actions (dict[str, Action]): Actions registered for this object.
        _tick_global (int): Global tick counter.
    """
    _object: 'ScheduledObject'
    _parent: 'ScheduledObject' = None
    tick: int = 0
    _t: float = 0
    _Ts: float = 0
    children: list['ScheduledObject'] = dataclasses.field(default_factory=list)
    events: dict = dataclasses.field(default_factory=dict)  # corrected default_factory from list to dict
    actions: dict[str, Action] = dataclasses.field(default_factory=dict)
    _tick_global: int = 0

    @property
    def tick_global(self):
        if self.parent is not None:
            return self.parent.scheduling.tick_global
        else:
            return self._tick_global

    @tick_global.setter
    def tick_global(self, value):
        if self.parent is None:
            self._tick_global = value

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value: 'ScheduledObject'):
        self._parent = value
        if self._parent is not None:
            self._parent.addChild(self._object)

    @property
    def t(self):
        return self.tick_global * self.Ts

    @t.setter
    def t(self, value):
        if self.parent is None:
            self._t = value

    @property
    def Ts(self):
        if self.parent is not None:
            return self.parent.scheduling.Ts
        else:
            return self._Ts

    @Ts.setter
    def Ts(self, value):
        if self.parent is None:
            self._Ts = value


class SCHEDULING_DEFAULT_ACTIONS(enum.StrEnum):
    ENTRY = "entry"
    EXIT = "exit"
    START = "start"
    PAUSE = "pause"
    STOP = "stop"
    INIT = "init"
    STEP = 'step'


class ScheduledObject(ABC):
    """
    Abstract base class for objects that can be scheduled.

    Each ScheduledObject maintains its own scheduling data including actions and child objects.
    """
    scheduling: SchedulingData
    id: str  # Unique identifier for the object

    def __init__(self, object_id: str = None, parent=None, *args, **kwargs):
        self.scheduling = SchedulingData(_object=self)
        if object_id is None:
            object_id = f"{type(self).__name__}_{id(self)}"
        self.id = object_id

        # Create default actions.
        action_entry = Action(action_id=SCHEDULING_DEFAULT_ACTIONS.ENTRY, function=self.entry)
        action_exit = Action(action_id=SCHEDULING_DEFAULT_ACTIONS.EXIT, function=self.exit)
        action_start = Action(action_id=SCHEDULING_DEFAULT_ACTIONS.START, function=self.start)
        action_pause = Action(action_id=SCHEDULING_DEFAULT_ACTIONS.PAUSE, function=self.pause)
        action_stop = Action(action_id=SCHEDULING_DEFAULT_ACTIONS.STOP, function=self.stop)
        action_init = Action(action_id=SCHEDULING_DEFAULT_ACTIONS.INIT, function=self.init)

        action_step = Action(action_id=SCHEDULING_DEFAULT_ACTIONS.STEP, function=self.step)

        self.addAction(action_entry)
        self.addAction(action_exit)
        self.addAction(action_start)
        self.addAction(action_pause)
        self.addAction(action_stop)
        self.addAction(action_init)

        self.addAction(action_step)

        self.scheduling.parent = parent

    def registerCallback(self, event, callback, parameters):
        # TODO: Implement callback registration.
        pass

    def addAction(self, action: Action):
        """
        Register an action with this ScheduledObject.

        Args:
            action (Action): The action to register.
        """
        if not isinstance(action, Action):
            raise AssertionError("Action must be an instance of Action")
        if action.id in self.scheduling.actions:
            raise AssertionError(f"An action with id {action.id} is already registered.")
        self.scheduling.actions[action.id] = action
        action.object = self

    def addChild(self, child: 'ScheduledObject'):
        """
        Register a child ScheduledObject. Default actions of the child are linked to the parent's default actions.
        """
        child.scheduling.actions["entry"].addParent(self.scheduling.actions["entry"])
        child.scheduling.actions["exit"].addParent(self.scheduling.actions["exit"])
        child.scheduling.actions["start"].addParent(self.scheduling.actions["start"])
        child.scheduling.actions["pause"].addParent(self.scheduling.actions["pause"])
        child.scheduling.actions["stop"].addParent(self.scheduling.actions["stop"])
        child.scheduling.actions["init"].addParent(self.scheduling.actions["init"])
        self.scheduling.children.append(child)

    def removeChild(self, child: 'ScheduledObject'):
        """
        Remove a child ScheduledObject from this object.
        """
        child.scheduling.parent = None
        for key in ["entry", "exit", "start", "pause", "stop", "init"]:
            child.scheduling.actions[key].removeParent(self.scheduling.actions[key])
            self.scheduling.actions[key].removeAction(child.scheduling.actions[key])
        self.scheduling.children.remove(child)

    # Default actions (to be optionally overridden by subclasses)
    def entry(self, *args, **kwargs):
        self.scheduling.tick += 1
        pass

    def exit(self, *args, **kwargs):
        pass

    def start(self, *args, **kwargs):
        pass

    def pause(self, *args, **kwargs):
        pass

    def stop(self, *args, **kwargs):
        pass

    def step(self, *args, **kwargs):
        pass

    @abstractmethod
    def init(self):
        pass


@dataclasses.dataclass
class SimpyEvents:
    """
    Contains events used by the Simpy-based scheduler.
    """
    exit: simpy.Event = None
    halt: simpy.Event = None
    timeout: simpy.Event = None
    resume: simpy.Event = None
    reset: simpy.Event = None


class Scheduler:
    """
    The Scheduler drives the simulation by executing the scheduled Action(s) in the Simpy environment.

    Attributes:
        action (Action): The root action to be executed.
        simpy_env (simpy.Environment): The simulation environment.
        simpy_events (SimpyEvents): Events to control simulation flow.
        mode (str): Either 'fast' for non-real-time or 'rt' for real-time.
        Ts (float): The simulation sample time.
        tick (int): Current tick.
        steps (int): Total number of steps.
        thread (threading.Thread): Optional thread if running in a separate thread.
    """
    action: Action
    simpy_env: simpy.Environment
    simpy_events: SimpyEvents
    mode: str  # 'fast' or 'rt'
    Ts: float
    tick: int
    steps: int
    thread: threading.Thread

    def __init__(self, action: Action, mode: str = 'rt', Ts: float = 1):
        """
        Initialize the Scheduler.

        Args:
            action (Action): The root action to schedule.
            mode (str): 'rt' for real-time, 'fast' for fast simulation.
            Ts (float): Sample time.
        """
        self.action = action
        self.mode = mode
        self.Ts = Ts
        self.simpy_events = SimpyEvents()
        self.thread = None
        self._init()
        self.args = []
        self.kwargs = {}

    def run(self, steps=None, thread: bool = False, *args, **kwargs):
        """
        Run the scheduler.

        Args:
            steps (int, optional): Number of simulation steps.
            thread (bool): Whether to run in a separate thread.
            *args, **kwargs: Additional arguments passed to the root action.
        """
        self.args = args
        self.kwargs = kwargs

        if thread:
            self.thread = threading.Thread(target=self.run, args=[steps, False])
            self.thread.start()
            return

        if steps is not None:
            self.simpy_events.timeout = self.simpy_env.timeout(steps - 1)

        self.simpy_env.process(self._run())
        while True:
            try:
                self.simpy_env.run(until=simpy.AnyOf(self.simpy_env,
                                                     [self.simpy_events.timeout,
                                                      self.simpy_events.exit,
                                                      self.simpy_events.halt]))
            except KeyboardInterrupt:
                self.simpy_events.exit.succeed()

            if self.simpy_events.exit.processed:
                break
            elif self.simpy_events.timeout.processed:
                print("Simulation Exit (Timeout)")
                break
            elif self.simpy_events.halt.processed:
                self.simpy_events.halt = self.simpy_env.event()
                print("Simulation halted")
                raise Exception("Halt not implemented yet!")
            elif self.simpy_events.resume.processed:
                print("Simulation resumed")
                raise Exception("Resume not implemented yet!")

    def _init(self):
        if self.mode == 'rt':
            self.simpy_env = simpy.RealtimeEnvironment(factor=self.Ts, strict=False)
        elif self.mode == 'fast':
            self.simpy_env = simpy.Environment()

        self.simpy_events.reset = self.simpy_env.event()
        self.simpy_events.exit = self.simpy_env.event()
        self.simpy_events.halt = self.simpy_env.event()
        self.simpy_events.timeout = self.simpy_env.event()
        self.simpy_events.resume = self.simpy_env.event()

        self.tick = 0
        self.steps = 0

    def _run(self):
        while True:
            self._step(*self.args, **self.kwargs)
            yield self.simpy_env.timeout(1)

    def _step(self, *args, **kwargs):
        self.action(*args, **kwargs)


def registerActions(obj: ScheduledObject, parent_action: Action, default_actions: bool = False, exclude: list = None):
    """
    Recursively register all actions of a ScheduledObject to a given parent action.

    Args:
        obj (ScheduledObject): The object whose actions are to be registered.
        parent_action (Action): The action to set as parent.
        default_actions (bool): Whether to include default actions (those starting with '_').
        exclude (list): List of action identifiers to exclude.
    """
    for act_id, act in obj.scheduling.actions.items():
        if not default_actions and act_id.startswith("_"):
            continue
        if exclude and act_id in exclude:
            continue
        act.addParent(parent_action)
