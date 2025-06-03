import math

import numpy as np
import qmt
import threading
import time

# ----------------------------------------------------------------------------------------------------------------------
from applications.FRODO.experiments.frodo_experiments import FRODO_ExperimentHandler, FRODO_Experiments_CLI
from applications.FRODO.frodo_agent import FRODO_Agent, FRODO_Aruco_Measurements, FRODO_Measurement_Data
from applications.FRODO.tracker.assets import TrackedVisionRobot, TrackedAsset, TrackedOrigin
from applications.FRODO.tracker.tracker import Tracker
from extensions.cli.cli_gui import CLI_GUI_Server
from extensions.cli.src.cli import CommandSet, Command
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
from applications.FRODO.algorithm.centralized_ekf_sincos import CentralizedLocationAlgorithm, VisionAgent, \
    VisionAgentMeasurement

# ----------------------------------------------------------------------------------------------------------------------
setLoggerLevel('Sound', 'INFO')
# ----------------------------------------------------------------------------------------------------------------------

Ts = 0.2


# ======================================================================================================================
class FRODO_Static:
    id: str
    position: np.ndarray
    psi: float
    asset: TrackedOrigin

    def __init__(self, id: str, asset: TrackedOrigin):
        self.id = id
        self.asset = asset

    @property
    def position(self):
        return np.array([self.asset.position[0], self.asset.position[1]])

    @property
    def psi(self):
        return self.asset.psi


class FRODO_Application:
    agents: dict[str, FRODO_Agent]
    statics: dict[str, FRODO_Static]

    manager: FrodoManager
    tracker: (Tracker, None)
    cli_gui: CLI_GUI_Server

    read_worker_pool: WorkerPool

    experiment_handler: FRODO_ExperimentHandler

    plotter: (FRODO_Web_Interface, None)
    logger: Logger

    step: int = 0
    _exit: bool = False
    _thread: threading.Thread

    aruco_plotting_objects: dict

    algorithm_running: bool

    algorithm: CentralizedLocationAlgorithm
    algorithm_agents: dict[str, VisionAgent]

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

        self.aruco_plotting_objects = {}
        self.statics = {}

        # self._thread = threading.Thread(target=self._update_plot, daemon=True)
        self._thread = threading.Thread(target=self.update, daemon=True)

        # self.timer = PrecisionTimer(timeout=0.1, repeat=True, callback=self.update)

        self.algorithm = CentralizedLocationAlgorithm(Ts=Ts)
        self.algorithm_running = False

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
            time1 = time.time()
            # print(f"Update {self.step}")
            # Step 1: Read all agent's data
            data = self._read_agents(0.1)

            # Step 2: Analyze and correct the data
            processed_data = self._processAgentMeasurements(data)

            # Step 3: Plot the stuff
            self._plotData(processed_data)

            # Step 4: Do measurements for plotting

            # Step 5: Do the algorithm
            if self.algorithm_running:
                # Step 5.1: Fill the algorithm agents with the inputs and measurements
                self._prepareAlgorithmAgents(processed_data)
                self.algorithm.update()
                self._collectAlgorithmData()

            self.step += 1
            time_elapsed = time.time() - time1
            if time_elapsed > 0.2:
                print("RACE CONDITIONS")
            time.sleep(0.2 - time_elapsed)

    # ------------------------------------------------------------------------------------------------------------------
    def _prepareAlgorithmAgents(self, data):

        # Loop through the algorithm agents
        for id, algorithm_agent in self.algorithm_agents.items():

            # Make the measurements empty for the current estimation step
            algorithm_agent.measurements = []
            # Check if it is a static or an agent
            if id in self.agents:

                # if the agent has no measurements, skip it
                if id not in data:
                    continue

                # Set the input to zero (for now)
                algorithm_agent.input = np.asarray([0, 0])

                # Go through the measurements
                agent_measurements = data[id]['measurements']

                for object_id, measurement_data in agent_measurements.items():
                    # VisionAgentMeasurement

                    # TODO: Here is still an error sometimes
                    algorithm_measurement = VisionAgentMeasurement(
                        source=id,
                        source_index=self.algorithm.getAgentIndex(id),
                        target=object_id,
                        target_index=self.algorithm.getAgentIndex(object_id),
                        measurement=np.asarray([measurement_data['measurement_noisy']['position'][0],
                                                measurement_data['measurement_noisy']['position'][1],
                                                measurement_data['measurement_noisy']['psi']]),
                        measurement_covariance=np.diag([measurement_data['measurement_noisy']['position_uncertainty'],
                                                        measurement_data['measurement_noisy']['position_uncertainty'],
                                                        0.01])
                    )

                    algorithm_agent.measurements.append(algorithm_measurement)


            else:
                # Do nothing for statics now
                ...

    # ------------------------------------------------------------------------------------------------------------------
    def _collectAlgorithmData(self):
        # Get the agent's position data
        for agent_id, agent in self.agents.items():
            agent_estimated_state = self.algorithm.agents[agent_id].state

            # TODO: I think I should use the estimated state here
            agent.state_true.x = float(agent_estimated_state[0])
            agent.state_true.y = float(agent_estimated_state[1])
            agent.state_true.psi = float(agent_estimated_state[2])

            # Update the plotting item for the estimated state
            agent.estimated_plot_item.position = [agent.state_true.x, agent.state_true.y]
            agent.estimated_plot_item.psi = agent.state_true.psi

            agent.estimated_plot_covariance.mid = [agent.state_true.x, agent.state_true.y]
            covariance = self.algorithm.agents[agent_id].state_covariance[0:2, 0:2]
            eigenvalues, _ = np.linalg.eigh(covariance)
            confidence_scale = 2  # 95% confidence
            max_variance = np.max(eigenvalues)
            radius = confidence_scale * np.sqrt(max_variance)

            agent.estimated_plot_covariance.diameter = 2 * radius

    # ------------------------------------------------------------------------------------------------------------------
    def _startAlgorithm(self):

        # Start by building the agents
        self.algorithm_agents = {}

        index = 0
        initial_state_guess_agents = [0.01, 0.012, 0.002]

        # First, add the actual agents
        for agent_id, agent in self.agents.items():
            self.algorithm_agents[agent_id] = VisionAgent(id=agent_id,
                                                          index=index,
                                                          state=np.asarray(initial_state_guess_agents),
                                                          state_covariance=np.diag(np.asarray([100.1, 100.2, 100.3])),
                                                          input=np.asarray([0, 0]),
                                                          input_covariance=np.eye(2) * 1e-3,
                                                          measurements=[],
                                                          dynamics_noise=1e-2
                                                          )
            index += 1

        # # Now, add the static markers
        for static_id, static in self.statics.items():
            self.algorithm_agents[static_id] = VisionAgent(id=static_id,
                                                           index=index,
                                                           state=np.asarray(
                                                               [static.position[0], static.position[1], static.psi]),
                                                           state_covariance=np.diag(
                                                               np.asarray(
                                                                   [0.00011 ** 2, 0.000012 ** 2, 0.000013 ** 2])),
                                                           input=np.asarray([0, 0]),
                                                           input_covariance=np.eye(2) * 1e-6,
                                                           measurements=[],
                                                           dynamics_noise=1e-9
                                                           )
            index += 1

        # Add the plotting items to the algorithm group
        algorithm_group: Group = self.plotter.get_element_by_id('algorithm')
        algorithm_group.clear()

        for agent_id, agent in self.agents.items():
            algorithm_group.add_vision_agent(agent.estimated_plot_item)
            algorithm_group.add_circle(agent.estimated_plot_covariance)

        self.algorithm.init(agents=self.algorithm_agents)
        self.algorithm_running = True
        self.logger.important("Start Algorithm")
        speak("Start Algorithm")

    # ------------------------------------------------------------------------------------------------------------------
    def _stopAlgorithm(self):

        # Clear the algorithm plotting group
        algorithm_group: Group = self.plotter.get_element_by_id('algorithm')
        algorithm_group.clear()

        self.algorithm_running = False
        self.logger.important("Stop Algorithm")
        speak("Stop Algorithm")

    # ------------------------------------------------------------------------------------------------------------------
    def _resetAlgorithm(self):
        self._stopAlgorithm()
        self._startAlgorithm()

    # ------------------------------------------------------------------------------------------------------------------
    def _plotData(self, data):

        aruco_group: Group = self.plotter.get_element_by_id('aruco_objects')
        optitrack_group: Group = self.plotter.get_element_by_id('optitrack')

        # Go through all aruco objects and set update=False
        for element_id, element in self.aruco_plotting_objects.items():
            element['updated'] = False

        for agent_id, agent_data in data.items():
            # print(f"Plotting data for {agent_id}")

            for object_id, measurement_data in agent_data['measurements'].items():
                # print(f"Plotting the measurement for {agent_id} -> {object_id}")
                if not 'measurement_actual' in measurement_data:
                    continue

                measured_position = agent_data['true_position'] + rotate_vector(
                    measurement_data['measurement_noisy']['position'], agent_data['true_psi'])

                plotted_marker_type = 'point' if measurement_data['type'] == 'static' else 'agent'
                plotted_marker_id = f"{agent_id}_{object_id}"

                if not plotted_marker_id in self.aruco_plotting_objects:
                    # Make a new object
                    self.aruco_plotting_objects[plotted_marker_id] = {}

                    if plotted_marker_type == 'point':

                        # plot the point
                        self.aruco_plotting_objects[plotted_marker_id]['element'] = aruco_group.add_point(
                            id=plotted_marker_id,
                            x=float(measured_position[0]),
                            y=float(measured_position[1]),
                            alpha=0.1
                        )

                        # plot the measurement line
                        self.aruco_plotting_objects[plotted_marker_id]['line'] = aruco_group.add_line(
                            id=f"{plotted_marker_id}_line",
                            start=(
                                self.agents[agent_id].estimated_plot_item
                                if self.algorithm_running
                                else optitrack_group.get_element_by_id(agent_id)),
                            end=optitrack_group.get_element_by_id(object_id),
                        )

                        self.aruco_plotting_objects[plotted_marker_id]['updated'] = True

                    else:
                        self.aruco_plotting_objects[plotted_marker_id]['element'] = aruco_group.add_point(
                            id=plotted_marker_id,
                            x=float(measured_position[0]),
                            y=float(measured_position[1]),
                            alpha=0.1,
                        )

                        # plot the measurement line
                        self.aruco_plotting_objects[plotted_marker_id]['line'] = aruco_group.add_line(
                            id=f"{plotted_marker_id}_line",
                            start=(
                                self.agents[agent_id].estimated_plot_item
                                if self.algorithm_running
                                else optitrack_group.get_element_by_id(agent_id)),
                            end=(
                                self.agents[object_id].estimated_plot_item
                                if self.algorithm_running
                                else optitrack_group.get_element_by_id(object_id)),
                        )

                        self.aruco_plotting_objects[plotted_marker_id]['updated'] = True


                else:
                    if plotted_marker_type == 'point':
                        element = aruco_group.get_element_by_id(plotted_marker_id)
                        if element is not None:
                            element.x = float(measured_position[0])
                            element.y = float(measured_position[1])
                        self.aruco_plotting_objects[plotted_marker_id]['updated'] = True
                    else:
                        element = aruco_group.get_element_by_id(plotted_marker_id)
                        if element is not None:
                            element.x = float(measured_position[0])
                            element.y = float(measured_position[1])
                        self.aruco_plotting_objects[plotted_marker_id]['updated'] = True

        # No gow through the aruco plotting objects and delete all that have not been updated
        for element_id in list(self.aruco_plotting_objects.keys()):
            element = self.aruco_plotting_objects[element_id]
            if not element['updated']:
                aruco_group.remove_element_by_id(element_id)
                aruco_group.remove_element_by_id(f"{element_id}_line")
                del self.aruco_plotting_objects[element_id]

    # ------------------------------------------------------------------------------------------------------------------
    def _processAgentMeasurements(self, data: dict[str, FRODO_Measurement_Data]):

        out = {}
        for agent_id, measurement_data in data.items():

            # print(f"Processing measurements for agent {agent_id}")
            out[agent_id] = {}

            true_position_agent = np.array([self.agents[agent_id].state_true.x, self.agents[agent_id].state_true.y])
            true_psi_agent = self.agents[agent_id].state_true.psi

            out[agent_id]['true_position'] = true_position_agent
            out[agent_id]['true_psi'] = true_psi_agent

            # Process the Aruco measurements
            aruco_measurements: list[FRODO_Aruco_Measurements] = measurement_data.aruco_measurements
            out[agent_id]['measurements'] = {}

            for measurement in aruco_measurements:
                # Let's see if we know this marker
                object_id, object_def, psi_offset = frodo_definitions.get_object_from_marker_id(measurement.marker_id)

                if object_id is None:
                    continue

                object_type = object_def.get('type', None)

                out[agent_id]['measurements'][object_id] = {}

                # print(f"Frodo {agent_id} measures {object_id} of type {object_type}")

                # Get the true position for the current agent and the measured object

                # print(f"The true position of the agent is [{true_position_agent[0]:.1f},{true_position_agent[1]:.1f}]")

                # Get the true position of the other thing. First check if it's an agent or a static

                if object_type == 'robot':
                    if object_id in self.agents:
                        true_position_object = np.array(
                            [self.agents[object_id].state_true.x, self.agents[object_id].state_true.y])
                        true_psi_object = self.agents[object_id].state_true.psi
                    else:
                        continue
                elif object_type == 'static':
                    true_position_object = self.tracker.tracked_assets[object_id].position
                    true_psi_object = self.tracker.tracked_assets[object_id].psi
                    # print(f"The objects data is {data}")
                else:
                    self.logger.warning(f"Object {object_id} is neither an agent nor a static object")
                    continue

                out[agent_id]['measurements'][object_id]['type'] = object_type

                # Get the actual measurement
                out[agent_id]['measurements'][object_id]['measurement_actual'] = {}
                out[agent_id]['measurements'][object_id]['measurement_actual']['position'] = measurement.translation_vec
                out[agent_id]['measurements'][object_id]['measurement_actual'][
                    'position_uncertainty'] = measurement.tvec_uncertainty
                out[agent_id]['measurements'][object_id]['measurement_actual']['psi'] = measurement.psi

                # Calculate the "true" measurement
                calculated_position_measurement = rotate_vector(true_position_object - true_position_agent,
                                                                -true_psi_agent)

                out[agent_id]['measurements'][object_id]['measurement_ideal'] = {}
                out[agent_id]['measurements'][object_id]['measurement_ideal'][
                    'position'] = calculated_position_measurement
                out[agent_id]['measurements'][object_id]['measurement_ideal']['psi'] = true_psi_object - true_psi_agent

                out[agent_id]['measurements'][object_id]['measurement_noisy'] = {}

                uncertainty_distance = measurement.tvec_uncertainty
                simulated_noise = np.random.normal(loc=0.0, scale=(uncertainty_distance / 10), size=2)


                # HERE I DO MY NASTY BUSINESS:
                alpha = 0.7
                noisy_calculated_measurement = calculated_position_measurement + simulated_noise
                noisy_calculated_measurement = alpha * calculated_position_measurement + (1 - alpha) * np.asarray(
                    measurement.translation_vec)

                out[agent_id]['measurements'][object_id]['measurement_noisy']['position'] = noisy_calculated_measurement
                out[agent_id]['measurements'][object_id]['measurement_noisy']['psi'] = \
                    out[agent_id]['measurements'][object_id]['measurement_ideal']['psi']
                out[agent_id]['measurements'][object_id]['measurement_noisy'][
                    'position_uncertainty'] = measurement.tvec_uncertainty

        return out

    # ------------------------------------------------------------------------------------------------------------------
    def _getRootCLISet(self):

        command_set_robots = FrodoManager_Commands(self.manager)

        start_algorithm_command = Command("start",
                                          callback=self._startAlgorithm,
                                          arguments=[],
                                          description="Starts the algorithm")

        stop_algorithm_command = Command("stop",
                                         callback=self._stopAlgorithm,
                                         arguments=[],
                                         description="Stops the algorithm")

        reset_algorithm_command = Command("reset",
                                          callback=self._resetAlgorithm,
                                          arguments=[],
                                          description="Resets the algorithm")

        command_set_algorithm = CommandSet('algorithm', commands=[start_algorithm_command,
                                                                  stop_algorithm_command,
                                                                  reset_algorithm_command])

        command_set_experiments = FRODO_Experiments_CLI(self.experiment_handler)

        command_set_root = CommandSet('.',
                                      child_sets=[command_set_robots,
                                                  command_set_algorithm,
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

            elif isinstance(asset, TrackedOrigin):
                if self.plotter:
                    optitrack_element = optitrack_group.get_element_by_id(id)
                    if optitrack_element is not None and isinstance(optitrack_element, plotter.Point):
                        optitrack_element.x = float(asset.position[0])
                        optitrack_element.y = float(asset.position[1])

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

                if isinstance(asset, TrackedOrigin):
                    optitrack_group.add_point(id=id,
                                              x=0.0,
                                              y=0.0,
                                              color=[0.5, 0.5, 0.5])

                    self.statics[id] = FRODO_Static(id=id, asset=asset)

    # ------------------------------------------------------------------------------------------------------------------
    def _prepare_plotting(self):
        self.plotter.add_rectangle(id='testbed', mid=[0, 0], x=3, y=3, fill=[0.9, 0.9, 0.9])
        group_robots: Group = self.plotter.add_group(id='robots')
        self.plotter.add_group(id='optitrack')
        self.plotter.add_group(id='algorithm')
        self.plotter.add_group(id='agents')
        self.plotter.add_group(id='aruco_objects')

        self.plotter.add_video("FRODO 1", "frodo1", 5000, placeholder=False)
        self.plotter.add_video("FRODO 2", "frodo2", 5000, placeholder=False)
        self.plotter.add_video("FRODO 3", "frodo3", 5000, placeholder=False)
        self.plotter.add_video("TESTBED", "localhost", 8199, placeholder=False)

    # ------------------------------------------------------------------------------------------------------------------
    def _read_agents(self, timeout):
        if self.read_worker_pool is None or len(self.read_worker_pool.workers) != len(self.agents):
            self._set_agent_read_pool()
        else:
            self.read_worker_pool.reset()

        self.read_worker_pool.start()
        results = self.read_worker_pool.wait(timeout=timeout)

        if not all(results):
            self.logger.warning(f"Read Agents: Not all workers finished successfully: {results}")
            self.logger.warning(f"Errors: {self.read_worker_pool.errors}")

        data = {}

        for id, agent in self.agents.items():
            data[id] = agent.measurements

        return data

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
