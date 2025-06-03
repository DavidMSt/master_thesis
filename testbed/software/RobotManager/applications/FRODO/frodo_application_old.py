import math
import qmt
import threading
import time


from applications.FRODO.experiments.frodo_experiments import FRODO_ExperimentHandler, FRODO_Experiments_CLI
from applications.FRODO.frodo_agent import FRODO_Agent, FRODO_Aruco_Measurements
from applications.FRODO.tracker.assets import TrackedVisionRobot, TrackedAsset
from applications.FRODO.tracker.tracker import Tracker
from extensions.cli.cli_gui import CLI_GUI_Server
from extensions.cli.src.cli import CommandSet
from robots.frodo.frodo import Frodo
from robots.frodo.frodo_definitions import get_title_from_marker
from robots.frodo.frodo_manager import FrodoManager
from robots.frodo.utils.frodo_cli import FRODO_CommandSet
from robots.frodo.utils.frodo_manager_cli import FrodoManager_Commands
from core.utils.callbacks import Callback
from core.utils.exit import register_exit_callback
from applications.FRODO.utilities.web_gui.FRODO_Web_Interface import FRODO_Web_Interface, Group
from core.utils.sound.sound import SoundSystem
from core.utils.sound.sound import speak
from core.utils.thread_worker import ThreadWorker, WorkerPool
from core.utils.logging_utils import Logger, setLoggerLevel
import robots.frodo.frodo_definitions as frodo_definitions
# import utils.orientation.plot_2d.dynamic.dynamic_2d_plotter as plotter
import applications.FRODO.utilities.web_gui.FRODO_Web_Interface as plotter
from core.utils.orientation.orientation_2d import rotate_vector

setLoggerLevel('Sound', 'INFO')

time1 = time.perf_counter()


# ======================================================================================================================
class FRODO_Application:
    agents: dict[str, FRODO_Agent]
    manager: FrodoManager
    tracker: (Tracker, None)
    cli_gui: CLI_GUI_Server

    read_worker_pool: WorkerPool

    experiment_handler: FRODO_ExperimentHandler

    plotter: (FRODO_Web_Interface, None)
    logger: Logger

    _exit: bool = False
    _thread: threading.Thread

    # === CONSTRUCTOR ==================================================================================================
    def __init__(self, enable_tracking: bool = True, start_webapp=True):
        self.manager = FrodoManager()
        self.manager.callbacks.new_robot.register(self._new_robot_callback)
        self.manager.callbacks.robot_disconnected.register(self._robot_disconnected_callback)

        self.agents = {}
        self.read_worker_pool = None

        if enable_tracking:
            self.tracker = Tracker()
        else:
            self.tracker = None

        if self.tracker:
            self.tracker.callbacks.new_sample.register(self._tracker_new_sample)
            self.tracker.callbacks.description_received.register(self._tracker_description_received)

        self.experiment_handler = FRODO_ExperimentHandler(self.manager, self.tracker, self.agents)

        self.cli_gui = CLI_GUI_Server(address='localhost', port=8090)

        # -- IO --
        self.logger = Logger('APP')
        self.logger.setLevel('INFO')
        self.soundsystem = SoundSystem(primary_engine='etts')
        self.soundsystem.start()

        if start_webapp:
            self.plotter = FRODO_Web_Interface()
        else:
            self.plotter = None

        # self._thread = threading.Thread(target=self._update_plot, daemon=True)
        self._thread = threading.Thread(target=self.update, daemon=True)

        # self.timer = PrecisionTimer(timeout=0.1, repeat=True, callback=self.update)

        register_exit_callback(self.close)

    # === METHODS ======================================================================================================
    def init(self):
        self.manager.init()

        if self.tracker:
            self.tracker.init()

        self._getRootCLISet()

    # ------------------------------------------------------------------------------------------------------------------
    def start(self):
        self.manager.start()
        self.cli_gui.start()
        self._thread.start()

        if self.plotter:
            self.plotter.start()
            self._prepare_plotting()

        if self.tracker:
            self.tracker.start()

        # self._thread.start()
        # self.timer.start()
        speak("Start Frodo Application")

    # ------------------------------------------------------------------------------------------------------------------
    def close(self, *args, **kwargs):
        speak("Closing Frodo Application")
        self._exit = True
        if self.plotter:
            self.plotter.close()
        time.sleep(2)

    # === METHODS ======================================================================================================
    def update(self):
        while not self._exit:

            # Step 1: Read all agent's data



            time.sleep(0.2)

    # ------------------------------------------------------------------------------------------------------------------
    def _getRootCLISet(self):

        command_set_robots = FrodoManager_Commands(self.manager)

        command_set_optitrack = CommandSet('optitrack',
                                           commands=[])

        command_set_joysticks = CommandSet('joysticks',
                                           commands=[])

        command_set_experiments = FRODO_Experiments_CLI(self.experiment_handler)


        command_set_root = CommandSet('.',
                                      child_sets=[command_set_robots,
                                                  command_set_optitrack,
                                                  command_set_joysticks,
                                                  command_set_experiments])



        self.cli_gui.updateCLI(command_set_root)

    # ------------------------------------------------------------------------------------------------------------------
    def _robot_disconnected_callback(self, robot):
        speak(f'Robot {robot.group_id} disconnected')
        self.cli_gui.sendLog(f'Robot {robot.group_id} disconnected')

        if robot.group_id in self.cli_gui.cli.root_set.child_sets['robots'].child_sets:
            self.cli_gui.cli.root_set.child_sets['robots'].removeChild(robot.group_id)
            self.cli_gui.updateCLI()

        # Remove the agent
        if robot.group_id in self.agents:
            del self.agents[robot.group_id]
            self.plotter.remove_element_by_id(f'agents/{robot.group_id}')

    # ------------------------------------------------------------------------------------------------------------------
    def _new_robot_callback(self, robot: Frodo):
        speak(f"New Robot {robot.id} connected")
        self.cli_gui.sendLog(f'New Robot {robot.id} connected')

        # Add a new agent
        agent = FRODO_Agent(id=robot.id, robot=robot)
        self.agents[robot.id] = agent

        if self.plotter:
            group_agents: Group = self.plotter.get_element_by_id('agents')
            group_agent = group_agents.add_group(id=robot.id)
            group_agent.add_vision_agent(id=f'{robot.id}_true',
                                         position=[0, 0],
                                         psi=0,
                                         vision_radius=1.5,
                                         vision_fov=math.radians(120),
                                         color=frodo_definitions.frodo_colors[robot.id])

        # Get the command set
        command_set_robot = FRODO_CommandSet(robot)
        self.cli_gui.cli.root_set.child_sets['robots'].addChild(command_set_robot)
        self.cli_gui.updateCLI()

    # ------------------------------------------------------------------------------------------------------------------
    def _tracker_new_sample(self, sample: dict[str, TrackedAsset]):
        optitrack_group: Group = self.plotter.get_element_by_id('optitrack')
        for id, asset in sample.items():
            if isinstance(asset, TrackedVisionRobot):

                # Update the plot
                if self.plotter:
                    optitrack_element = optitrack_group.get_element_by_id(id)
                    if optitrack_element is not None and isinstance(optitrack_element, plotter.VisionAgent):
                        optitrack_element.position = [float(asset.position[0]), float(asset.position[1])]
                        optitrack_element.psi = asset.psi

                # Update the agent
                if id in self.agents:
                    self.agents[id].updateRealState(x=asset.position[0], y=asset.position[1], psi=asset.psi)

                    # Update the real agents position in the plot
                    if self.plotter:
                        agent_element = self.plotter.get_element_by_id(f'agents/{id}/{id}_true')
                        if agent_element is not None and isinstance(agent_element, plotter.VisionAgent):
                            agent_element.position = [float(asset.position[0]), float(asset.position[1])]
                            agent_element.psi = asset.psi

    # ------------------------------------------------------------------------------------------------------------------
    def _tracker_description_received(self, assets):
        self.logger.info(f'Tracker Description Received')
        if self.plotter is not None:
            optitrack_group: Group = self.plotter.get_element_by_id('optitrack')
            for id, asset in assets.items():

                if isinstance(asset, TrackedVisionRobot):

                    if id in frodo_definitions.frodo_colors:
                        color = frodo_definitions.frodo_colors[id]
                    else:
                        color = [0.5, 0.5, 0.5]

                    optitrack_group.add_vision_agent(id=id,
                                                     position=[0, 0],
                                                     psi=0,
                                                     vision_radius=1.5,
                                                     vision_fov=math.radians(120),
                                                     color=color)

    # ------------------------------------------------------------------------------------------------------------------
    def _prepare_plotting(self):
        self.plotter.add_rectangle(id='testbed', mid=[0, 0], x=3, y=3, fill=[0.9, 0.9, 0.9])
        group_robots: Group = self.plotter.add_group(id='robots')
        self.plotter.add_group(id='optitrack')
        self.plotter.add_group(id='algorithm')
        self.plotter.add_group(id='agents')

        self.plotter.add_video("FRODO 1", "frodo1", 5000, placeholder=False)
        self.plotter.add_video("FRODO 2", "frodo2", 5000, placeholder=False)
        self.plotter.add_video("FRODO 3", "frodo3", 5000, placeholder=False)
        self.plotter.add_video("FRODO 4", "frodo4", 5000, placeholder=False)

    # ------------------------------------------------------------------------------------------------------------------
    def _plot_aruco_measurement(self, agent_key, agent_pos_global, agent_psi_global, measurement: FRODO_Aruco_Measurements, 
                                group_element, agent_element, aruco_objects_dict):
        marker_agent_name, additional_psi = get_title_from_marker(measurement.marker_id)
        if marker_agent_name is None:
            return None, None, None

        id = marker_agent_name + "BY" + agent_key
        agent_id = "a" + id
        line_id = "l" + id
        circle_id = "c" + id


        global_marker_tvec = rotate_vector(measurement.translation_vec, agent_psi_global)
        global_marker_pos = [float(agent_pos_global[0] + global_marker_tvec[0]), float(agent_pos_global[1] + global_marker_tvec[1])]

        global_marker_psi = qmt.wrapToPi(agent_psi_global + measurement.psi + additional_psi +  math.pi)

        '''check if marker was seen earlier'''
        if not agent_id in aruco_objects_dict:

            '''Add aruco_marker to known markers'''
            aruco_objects_dict[agent_id] = {'element': None}
            aruco_objects_dict[agent_id]['element'] = group_element.add_agent(id=agent_id, position=global_marker_pos,
                                                                        psi=global_marker_psi, color=[1, 0, 0])
            
            aruco_objects_dict[line_id] = {'element': None}
            aruco_objects_dict[line_id]['element'] = group_element.add_line(line_id, start=agent_element,
                                    end=aruco_objects_dict[agent_id]['element'])
            
            aruco_objects_dict[circle_id] = {'element': None}
            aruco_objects_dict[circle_id]['element'] = group_element.add_circle(id=circle_id, mid=global_marker_pos, diameter=measurement.tvec_uncertainty)
            return None, None, None

        else:
            '''marker was seen earlier, update position'''
            aruco_objects_dict[agent_id]['element'].position = global_marker_pos
            aruco_objects_dict[agent_id]['element'].psi = global_marker_psi

            aruco_objects_dict[circle_id]['element'].mid = global_marker_pos
            aruco_objects_dict[circle_id]['element'].diameter = measurement.tvec_uncertainty


            return agent_id, circle_id, line_id

            

    def _aruco_marker_plotting(self, group_element, aruco_objects_dict):
        aruco_objects_copy = aruco_objects_dict.copy()
        '''copy of aruco_objects_dict to check if a marker is still visible'''

        '''loop through all connected agents'''
        for key, agent in self.agents.items():
            agent_element = self.plotter.get_element_by_id(f'/optitrack/{agent.id}')
            pos = agent_element.position
            psi = agent_element.psi
            measurements = agent.measurements.aruco_measurements
            
            '''loop through all aruco measurements'''
            for measurement in measurements:
                ids = self._plot_aruco_measurement(agent_key=key, 
                                                        agent_pos_global=pos,
                                                        agent_psi_global=psi,
                                                        measurement=measurement,
                                                        group_element=group_element,
                                                        agent_element=agent_element,
                                                        aruco_objects_dict=aruco_objects_dict)
                for id in ids:
                    if id is not None:
                        aruco_objects_copy.pop(id)

        for not_visible in aruco_objects_copy:
            '''remove all agents and points not seen this iteration'''
            aruco_objects_dict.pop(not_visible)
            group_element.remove_element_by_id(f'/{not_visible}')

    # ------------------------------------------------------------------------------------------------------------------
    def _update_plot(self):
        group_element = self.plotter.add_group(id='aruco_objects')
        '''Aruco Object Group Element'''
        aruco_objects = {}
        '''Dictionary containing all sensed Markers'''

        while not self._exit:
            self._read_agents(0.1)
            self._aruco_marker_plotting(group_element=group_element, aruco_objects_dict=aruco_objects)
            time.sleep(0.2)
    
    
    # ------------------------------------------------------------------------------------------------------------------
    def _read_agents(self, timeout):
        if self.read_worker_pool == None or len(self.read_worker_pool.workers) != len(self.agents):
            self._set_agent_read_pool()
        else:
            self.read_worker_pool.reset()

        self.read_worker_pool.start()
        results = self.read_worker_pool.wait(timeout=timeout)
        #
        if not all(results):
            self.logger.warning(f"Read Agents: Not all workers finished successfully: {results}")
            self.logger.warning(f"Errors: {self.read_worker_pool.errors}")


    # ------------------------------------------------------------------------------------------------------------------
    def _set_agent_read_pool(self):
        workers = []
        for key, agent in self.agents.items():
            workers.append(ThreadWorker(start=False, function=Callback(function=agent.readRobotData)))
        pool = WorkerPool(workers)
        self.read_worker_pool = pool


# ======================================================================================================================
def start_frodo_application():
    app = FRODO_Application(enable_tracking=True, start_webapp=True)
    app.init()
    app.start()
    while True:
        time.sleep(20)


# ======================================================================================================================
if __name__ == '__main__':
    start_frodo_application()
