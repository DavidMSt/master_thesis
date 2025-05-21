import abc
import dataclasses
import math
import threading
import time

from applications.FRODO.algorithm.centralized_ekf_sincos import CentralizedLocationAlgorithm
# from applications.FRODO.frodo_agent import FRODO_Agent
from applications.FRODO.simulation.frodo_simulation import FRODO_Simulation, FRODO_SimulatedVisionAgent
from applications.FRODO.tracker.tracker import Tracker
from applications.FRODO.utilities.web_gui.FRODO_Web_Interface import FRODO_Web_Interface, Group
from core.utils.exit import register_exit_callback
from core.utils.logging_utils import Logger
from core.utils.sound.sound import SoundSystem
from extensions.cli.cli_gui import CLI_GUI_Server
from extensions.joystick.joystick_manager import JoystickManager
from robots.frodo.frodo import Frodo
from robots.frodo.frodo_manager import FrodoManager


# ======================================================================================================================
@dataclasses.dataclass
class FRODO_Agent_State:
    x: float = 0
    y: float = 0
    psi: float = 0
    v: float = 0
    psi_dot: float = 0


# ----------------------------------------------------------------------------------------------------------------------
class FRODO_Agent(abc.ABC):
    id: str
    state: FRODO_Agent_State

    def __init__(self, id: str):
        self.id = id

    @abc.abstractmethod
    def setInput(self, v, psi_dot):
        ...

    # @abc.abstractmethod
    # def getData(self):
    #     ...

    # @abc.abstractmethod
    # def getState(self):
    #     ...

    @abc.abstractmethod
    def getMeasurements(self):
        ...


# ----------------------------------------------------------------------------------------------------------------------
class FRODO_Agent_Real(FRODO_Agent):
    robot: Frodo

    def __init__(self, id: str, robot: Frodo):
        super().__init__(id)
        self.robot = robot

    def setInput(self, v, psi_dot):
        ...

    def getMeasurements(self):
        ...


# ----------------------------------------------------------------------------------------------------------------------
class FRODO_Agent_Virtual(FRODO_Agent):
    simulated_agent: FRODO_SimulatedVisionAgent

    def __init__(self, id: str, simulated_agent: FRODO_SimulatedVisionAgent):
        super().__init__(id)
        self.simulated_agent = simulated_agent

    def setInput(self, v, psi_dot):
        self.simulated_agent.input = [v, psi_dot]


    def getMeasurements(self):
        ...

# ======================================================================================================================
class FRODO_Application_Virtual:
    agents: dict[str, FRODO_Agent]

    simulation: FRODO_Simulation
    algorithm: CentralizedLocationAlgorithm

    real_robot_manager: FrodoManager
    tracker: Tracker

    cli_gui: CLI_GUI_Server

    web_interface: FRODO_Web_Interface

    logger: Logger

    joystick_manager: JoystickManager
    _exit: bool = False
    _thread: threading.Thread

    # === INIT =========================================================================================================
    def __init__(self, Ts: float = 0.1, enable_tracking: bool = True, start_webapp=True):

        self.Ts = Ts

        self.manager = FrodoManager()
        self.manager.callbacks.new_robot.register(self._new_robot_callback)
        self.manager.callbacks.robot_disconnected.register(self._robot_disconnected_callback)

        self.agents = {}

        self.simulation = FRODO_Simulation(self.Ts)
        self.simulation.logger.setLevel('DEBUG')
        self.simulation.logger.switchLoggingLevel('INFO', 'DEBUG')

        self.algorithm = CentralizedLocationAlgorithm(self.Ts)

        if enable_tracking:
            self.tracker = Tracker()
        else:
            self.tracker = None  # type: ignore

        if self.tracker:
            self.tracker.callbacks.new_sample.register(self._tracker_new_sample)
            self.tracker.callbacks.description_received.register(self._tracker_description_received)

        self.cli_gui = CLI_GUI_Server(address='localhost', port=8090)

        # -- IO --
        self.logger = Logger('APP')
        self.logger.setLevel('INFO')
        self.soundsystem = SoundSystem(primary_engine='etts')
        self.soundsystem.start()

        if start_webapp:
            self.web_interface = FRODO_Web_Interface()
        else:
            self.web_interface = None

        self.joystick_manager = JoystickManager()
        self.joystick_manager.callbacks.new_joystick.register(self._new_joystick_callback)
        self.joystick = None

        self._thread = threading.Thread(target=self._task, daemon=True)

        register_exit_callback(self.close)

    # === METHODS ======================================================================================================

    def init(self):
        self.simulation.init()
        self.joystick_manager.init()

    # ------------------------------------------------------------------------------------------------------------------
    def start(self):
        self.simulation.start()
        self.joystick_manager.start()
        self._thread.start()
        if self.web_interface is not None:
            self.web_interface.start()
            self._initWebInterface()
        self.soundsystem.speak("Start Frodo Application")

    # ------------------------------------------------------------------------------------------------------------------
    def close(self):
        self.soundsystem.speak("Close Frodo Application")
        self._exit = True
        if self._thread is not None and self._thread.is_alive():
            self._thread.join()
        time.sleep(3)

    # ------------------------------------------------------------------------------------------------------------------
    def addVirtualAgent(self, id, position, psi, vision_radius=1.5, vision_fov=math.radians(90),
                        color=None) -> FRODO_Agent_Virtual:

        if color is None:
            color = [0.5, 0.5, 0.5]

        virtual_agent = self.simulation.addVirtualAgent(id=id, fov_deg=vision_fov, view_range=vision_radius)
        virtual_agent.setPosition(position)
        virtual_agent.setOrientation(psi)

        agent = FRODO_Agent_Virtual(id=id, simulated_agent=virtual_agent)
        if id in self.agents:
            self.logger.error(f'Agent {id} already exists')

        group_simulation: Group = self.web_interface.get_element_by_id('simulation')

        group_simulation.add_vision_agent(id=id,
                                          position=position,
                                          psi=psi,
                                          vision_radius=vision_radius,
                                          vision_fov=vision_fov,
                                          color=color)

        self.agents[id] = agent
        self.logger.info(f'Added Virtual Agent {id}')

        return agent

    # ------------------------------------------------------------------------------------------------------------------
    def startAlgorithm(self):
        ...

    def stopAlgorithm(self):
        ...

    def resetAlgorithm(self):
        ...

    # === PRIVATE METHODS ==============================================================================================
    def _task(self):
        while not self._exit:

            # if self.joystick is not None:
            #     forward = -0.3 * self.joystick.getAxis("LEFT_VERTICAL")
            #     turn = -1.5 * self.joystick.getAxis("RIGHT_HORIZONTAL")
            #
            #     agent1 = self.simulation.agents.get('vfrodo1')
            #     if agent1 is not None:
            #         agent1.setInput(forward, turn)

            # 1. Collect data from all agents

            # 2. Update the algorithm
            self._updateAlgorithm()

            # 3. Handle inputs

            # 4. Update the web interface
            self._updateWebInterface()
            time.sleep(0.1)

    # ------------------------------------------------------------------------------------------------------------------
    def _updateAlgorithm(self):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def _new_robot_callback(self, robot):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def _robot_disconnected_callback(self, robot):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def _tracker_new_sample(self, sample):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def _tracker_description_received(self, description):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def _initWebInterface(self):
        self.web_interface.add_rectangle(id='testbed', mid=[0, 0], x=3, y=3, fill=[0.9, 0.9, 0.9])
        group_robots: Group = self.web_interface.add_group(id='robots')
        self.web_interface.add_group(id='optitrack')
        self.web_interface.add_group(id='algorithm')
        self.web_interface.add_group(id='agents')
        self.web_interface.add_group(id='simulation')

        self.web_interface.add_video("FRODO 1", "frodo1", 5000, placeholder=False)
        self.web_interface.add_video("FRODO 2", "frodo2", 5000, placeholder=False)
        self.web_interface.add_video("FRODO 3", "frodo3", 5000, placeholder=False)
        self.web_interface.add_video("FRODO 4", "frodo4", 5000, placeholder=False)

    # ------------------------------------------------------------------------------------------------------------------
    def _updateWebInterface(self):

        # 1. Update simulated Agents
        for id, agent in self.agents.items():
            if isinstance(agent, FRODO_Agent_Virtual):
                # Check if there is an object in the webinterface
                plot_object = self.web_interface.get_element_by_id(f'simulation/{id}')
                if plot_object is not None:
                    plot_object.position = agent.simulated_agent.getPosition()
                    plot_object.psi = agent.simulated_agent.getOrientation()

    def _new_joystick_callback(self, joystick):
        self.joystick = joystick


# ======================================================================================================================
def main():
    app = FRODO_Application_Virtual(Ts=0.1, enable_tracking=False, start_webapp=True)
    app.init()
    app.start()

    time.sleep(1)

    agent1 = app.addVirtualAgent(id='vfrodo1',
                                 position=[1, 1],
                                 psi=math.radians(120),
                                 vision_radius=1.5,
                                 vision_fov=math.radians(120),
                                 color=[0.7, 0, 0])

    # agent1.simulated_agent.input = [0.2, 0.2]

    agent2 = app.addVirtualAgent(id='vfrodo2',
                                 position=[0, 0],
                                 psi=math.radians(0),
                                 vision_radius=1.5,
                                 vision_fov=math.radians(100),
                                 color=[0, 0, 0.7])

    while True:
        time.sleep(1)


# ======================================================================================================================
if __name__ == '__main__':
    main()
