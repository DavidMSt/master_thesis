import datetime
import json
import os
import qmt
import re
import threading
import time


from applications.FRODO.frodo_agent import FRODO_Agent
from applications.FRODO.tracker.assets import TrackedVisionRobot
from applications.FRODO.tracker.tracker import Tracker
from extensions.cli.src.cli import Command, CommandSet, CommandArgument
from robots.frodo.frodo_manager import FrodoManager
from robots.frodo.frodo_definitions import get_title_from_marker
from core.utils.logging_utils import Logger
from core.utils.csv_utils import CSVLogger
from core.utils.sound.sound import speak, playSound

# INPUT_FILE_PATH = "./applications/FRODO/experiments/input/"
INPUT_FILE_PATH = "/Users/lehmann/Seafile/work/projects/testbed/bilbolab/testbed/software/RobotManager/applications/FRODO/experiments/input/"
OUTPUT_FILE_PATH = "/Users/lehmann/Seafile/work/projects/testbed/bilbolab/testbed/software/RobotManager/applications/FRODO/experiments/output/"

# OUTPUT_FILE_PATH = "./applications/FRODO/experiments/output/"

POSITION_TOLERANCE = 0.10   #[m]
PSI_TOLERANCE = 0.17    #[rad]; ~10°


logger = Logger('EXPERIMENT_HANDLER')
logger.setLevel('INFO')

ALL_VISIBLES = ['frodo1', 'frodo2', 'frodo3', 'frodo4', 'static1']
STD_VAL = None

def humanReadableDate():
    return datetime.datetime.now().strftime("%#d of %B %Y, %-I:%M %p and %S seconds")

def humanReadableTime():
    return datetime.datetime.now().strftime("%-I:%M %p and %S seconds")

def create_experiment_data_dict():
    '''create a dictionary with empty values for the experiment progress logging
    \nsee sample_step_data.py for structure example'''

    data_dict = {}
    data_dict['time'] = 0.0
    data_dict['marker'] = {'num': None, 'description': None}

    for asset in ALL_VISIBLES:
        
        data_dict[asset] = {}

        data_dict[asset]['optitrack'] = {}
        data_dict[asset]['optitrack']['valid'] = False
        data_dict[asset]['optitrack']['position'] = {"x": STD_VAL, "y": STD_VAL}
        data_dict[asset]['optitrack']['psi'] = STD_VAL

        if "static" not in asset:
            data_dict[asset]['agent'] = {}
            data_dict[asset]['agent']['valid'] = False
            data_dict[asset]['agent']['state_true'] = {}
            data_dict[asset]['agent']['state_true']['position'] = {"x": STD_VAL, "y": STD_VAL}
            data_dict[asset]['agent']['state_true']['psi'] = STD_VAL
            data_dict[asset]['agent']['state_true']['v'] = STD_VAL
            data_dict[asset]['agent']['state_true']['psi_dot'] = STD_VAL
            
            data_dict[asset]['agent']['state_estimated'] = {}
            data_dict[asset]['agent']['state_estimated']['position'] = {"x": STD_VAL, "y": STD_VAL}
            data_dict[asset]['agent']['state_estimated']['psi'] = STD_VAL
            data_dict[asset]['agent']['state_estimated']['v'] = STD_VAL
            data_dict[asset]['agent']['state_estimated']['psi_dot'] = STD_VAL
            data_dict[asset]['agent']['state_estimated']['uncertainty'] = STD_VAL

            data_dict[asset]['measurement'] = {}
            data_dict[asset]['measurement']['time'] = STD_VAL
            data_dict[asset]['measurement']['speed_left'] = STD_VAL
            data_dict[asset]['measurement']['speed_right'] = STD_VAL
            data_dict[asset]['measurement']['rpm_left'] = STD_VAL
            data_dict[asset]['measurement']['rpm_right'] = STD_VAL
            
            

            for measured_asset in ALL_VISIBLES:

                data_dict[asset]['measurement'][measured_asset] = {}
                data_dict[asset]['measurement'][measured_asset]['visible'] = False
                data_dict[asset]['measurement'][measured_asset]['tvec'] = {"x": STD_VAL, "y": STD_VAL}
                data_dict[asset]['measurement'][measured_asset]['psi'] = STD_VAL
                data_dict[asset]['measurement'][measured_asset]['tvec_uncertainty'] = STD_VAL
                data_dict[asset]['measurement'][measured_asset]['psi_uncertainty'] = STD_VAL

    return data_dict
        
        


class FRODO_ExperimentHandler:
    manager                     : FrodoManager
    tracker                     : Tracker
    agents                      : dict[str, FRODO_Agent]

    logging_marker              : int
    logging_marker_count        : int
    logging_marker_description  : str
    csv_logger                  : CSVLogger
    experiment_log_data         : dict

    config                      : json
    experiment_agents           : list
    movements                   : list

    start_time                  : float
    experiment_name             : str
    output_directory_path       : str

    logging_thread              : threading.Thread
    _stopped                    : bool

    def __init__(self, manager : FrodoManager, tracker : Tracker, agents : dict[str, FRODO_Agent]):
        self.manager = manager
        self.tracker = tracker
        self.agents = agents

        self.logging_marker_description = None
        self.logging_marker = 0
        self.logging_marker_count = 0
        self.csv_logger = None
        self.experiment_log_data = create_experiment_data_dict()

        self.experiment_agents = []
        self.output_directory_path = None
        self.experiment_name = None

        self._stopped = False
        self.logging_thread = None

    def _logging_task(self):
        self.csv_logger.make_file(self.experiment_name + ".csv", self.output_directory_path)

        while not self._stopped:
            self.getStepData()
            self.csv_logger.write_data(self.experiment_log_data)
            time.sleep(1)

    def startCsvLogging(self):
        self._stopped = False
        self.csv_logger = CSVLogger()
        self.logging_thread = threading.Thread(target=self._logging_task, daemon=True)
        self.logging_thread.start()

    def stopCsvLogging(self):
        self._stopped = True
        self.logging_marker_description = None
        self.logging_marker = None
        self.logging_marker_count = 0
        if self.logging_thread is not None:
            self.logging_thread.join()
        self.csv_logger.close()

    def markLogger(self, description):
        self.logging_marker_count += 1
        self.logging_marker = self.logging_marker_count
        self.logging_marker_description = description
        
        speak(f"Set marker {self.logging_marker_count} at {humanReadableTime()}, Description: {self.logging_marker_description}")
        
    def getStepData(self):
        '''update experiment_log_data to contain current experiment state'''

        '''update time'''
        self.experiment_log_data['time'] = time.time() - self.start_time
        self.experiment_log_data['marker'] = {'num': self.logging_marker, 'description': self.logging_marker_description}
        self.logging_marker = None
        self.logging_marker_description = None

        '''update optitrack data'''
        for key, asset in self.tracker.assets.items():
            self.experiment_log_data[key]['optitrack']['valid'] = asset.tracking_valid
            self.experiment_log_data[key]['optitrack']['position']['x'] = float(asset.position[0])
            self.experiment_log_data[key]['optitrack']['position']['y'] = float(asset.position[1])
            if isinstance(asset, TrackedVisionRobot):
                self.experiment_log_data[key]['optitrack']['psi'] = float(asset.psi)


        '''keep track of unconnected agents'''
        unconnected_agents = ALL_VISIBLES.copy()
        '''filter static agents'''
        regex = re.compile('[{}]'.format("static"))
        unconnected_agents = list(filter(lambda x: not regex.search(x), unconnected_agents))
        '''update robot data'''
        for key, agent in self.agents.items():

            self.experiment_log_data[key]['agent']['valid'] = True
            
            self.experiment_log_data[key]['agent']['state_true']['position']['x'] = float(agent.state_true.x)
            self.experiment_log_data[key]['agent']['state_true']['position']['y'] = float(agent.state_true.y)
            self.experiment_log_data[key]['agent']['state_true']['psi'] = float(agent.state_true.psi)
            self.experiment_log_data[key]['agent']['state_true']['v'] = float(agent.state_true.v)
            self.experiment_log_data[key]['agent']['state_true']['psi_dot'] = float(agent.state_true.psi_dot)
            
            self.experiment_log_data[key]['agent']['state_estimated']['position']['x'] = float(agent.state_estimated.x)
            self.experiment_log_data[key]['agent']['state_estimated']['position']['y'] = float(agent.state_estimated.y)
            self.experiment_log_data[key]['agent']['state_estimated']['psi'] = float(agent.state_estimated.psi)
            self.experiment_log_data[key]['agent']['state_estimated']['v'] = float(agent.state_estimated.v)
            self.experiment_log_data[key]['agent']['state_estimated']['psi_dot'] = float(agent.state_estimated.psi_dot)
            self.experiment_log_data[key]['agent']['state_estimated']['uncertainty'] = 42.0 #TODO set to real value
            
            if key in unconnected_agents:
                unconnected_agents.remove(key)

            self.experiment_log_data[key]['measurement']['time'] = float(agent.measurements.time)
            self.experiment_log_data[key]['measurement']['speed_left'] = float(agent.measurements.speed_l)
            self.experiment_log_data[key]['measurement']['speed_right'] = float(agent.measurements.speed_r)
            self.experiment_log_data[key]['measurement']['rpm_left'] = float(agent.measurements.rpm_l)
            self.experiment_log_data[key]['measurement']['rpm_right'] = float(agent.measurements.rpm_r)

            '''keep track of unseen agents'''
            unseen_aruco_measurement_agents = ALL_VISIBLES.copy()

            for measurement in agent.measurements.aruco_measurements:
                measured_key, additional_psi = get_title_from_marker(measurement.marker_id)
                if measured_key is None:
                    continue
                self.experiment_log_data[key]['measurement'][measured_key]['visible'] = True
                self.experiment_log_data[key]['measurement'][measured_key]['tvec']['x'] = float(measurement.translation_vec[0])
                self.experiment_log_data[key]['measurement'][measured_key]['tvec']['y'] = float(measurement.translation_vec[1])
                self.experiment_log_data[key]['measurement'][measured_key]['psi'] = float(qmt.wrapToPi(measurement.psi + additional_psi))
                self.experiment_log_data[key]['measurement'][measured_key]['tvec_uncertainty'] = float(measurement.tvec_uncertainty)
                self.experiment_log_data[key]['measurement'][measured_key]['psi_uncertainty'] = float(measurement.psi_uncertainty)
                
                if measured_key in unseen_aruco_measurement_agents:
                    unseen_aruco_measurement_agents.remove(measured_key)
            
            '''set visible for all unseen agents'''
            for unseen_aruco_measurement_agent in unseen_aruco_measurement_agents:
                self.experiment_log_data[key]['measurement'][unseen_aruco_measurement_agent]['visible'] = False
                self.experiment_log_data[key]['measurement'][unseen_aruco_measurement_agent]['tvec']['x'] = STD_VAL
                self.experiment_log_data[key]['measurement'][unseen_aruco_measurement_agent]['tvec']['y'] = STD_VAL
                self.experiment_log_data[key]['measurement'][unseen_aruco_measurement_agent]['psi'] = STD_VAL
                self.experiment_log_data[key]['measurement'][unseen_aruco_measurement_agent]['tvec_uncertainty'] = STD_VAL
                self.experiment_log_data[key]['measurement'][unseen_aruco_measurement_agent]['psi_uncertainty'] = STD_VAL
                
        '''set valid for all unconnected agents'''
        for unconnected_agent in unconnected_agents:
            self.experiment_log_data[unconnected_agent]['agent']['valid'] = False
            self.experiment_log_data[unconnected_agent]['agent']['state_true']['position']['x'] = STD_VAL
            self.experiment_log_data[unconnected_agent]['agent']['state_true']['position']['y'] = STD_VAL
            self.experiment_log_data[unconnected_agent]['agent']['state_true']['psi'] = STD_VAL
            self.experiment_log_data[unconnected_agent]['agent']['state_true']['v'] = STD_VAL
            self.experiment_log_data[unconnected_agent]['agent']['state_true']['psi_dot'] = STD_VAL
            
            self.experiment_log_data[unconnected_agent]['agent']['state_estimated']['position']['x'] = STD_VAL
            self.experiment_log_data[unconnected_agent]['agent']['state_estimated']['position']['y'] = STD_VAL
            self.experiment_log_data[unconnected_agent]['agent']['state_estimated']['psi'] = STD_VAL
            self.experiment_log_data[unconnected_agent]['agent']['state_estimated']['v'] = STD_VAL
            self.experiment_log_data[unconnected_agent]['agent']['state_estimated']['psi_dot'] = STD_VAL
            self.experiment_log_data[unconnected_agent]['agent']['state_estimated']['uncertainty'] = STD_VAL

            self.experiment_log_data[unconnected_agent]['measurement']['time'] = STD_VAL
            self.experiment_log_data[unconnected_agent]['measurement']['speed_left'] = STD_VAL
            self.experiment_log_data[unconnected_agent]['measurement']['speed_right'] = STD_VAL
            self.experiment_log_data[unconnected_agent]['measurement']['rpm_left'] = STD_VAL
            self.experiment_log_data[unconnected_agent]['measurement']['rpm_right'] = STD_VAL


        
            

    def checkConsistency(self):


        check_passed = True

        tracked_assets = self.config['requirements']['tracked_assets']
        required_agents = self.config['requirements']['agents'].keys()
        required_statics = self.config['requirements']['statics'].keys()
        algorithm_agents = self.config['algorithm']['agents'].keys()
        algorithm_statics = self.config['algorithm']['statics'].keys()
        movement_agents = self.config['movement'].keys()
        
        for agent in required_agents:
            '''Check if required agents appear in all config parts'''
            if not agent in tracked_assets:
                logger.info(f"Found required agent {agent} that is not \
                                part of requirements::tracked_assets!")
                check_passed = False
            if not agent in algorithm_agents:
                logger.info(f"Found required agent {agent} that is not \
                                part of algorithm::agents!")
                check_passed = False
            if not agent in movement_agents:
                logger.info(f"Found required agent {agent} that is not \
                                part of movement!")
                check_passed = False
                    
            if check_passed:
                self.experiment_agents.append(agent)
        
        for static in required_statics:
            '''Check if required agents appear in all config parts'''
            if not static in tracked_assets:
                logger.info(f"Found required static {static} that is not \
                                part of requirements::tracked_assets!")
                check_passed = False
            if not static in algorithm_statics:
                logger.info(f"Found required static {static} that is not \
                                part of algorithm::statics!")
                check_passed = False

        return check_passed



    def checkRequiredPositions(self):

        if not self.tracker:
            return True

        check_passed = True
        required_assets = self.config['requirements']['tracked_assets']
        required_statics = self.config['requirements']['statics'].keys()

        for asset_str in required_assets:
            try:
                asset_type = "agents"
                if asset_str in required_statics:
                    asset_type = "statics"

                if asset_str not in self.tracker.assets:
                    logger.warning(f"Required asset {asset_str} not part of OptiTrack Data!")
                    check_passed = False
                    continue
                
                asset = self.tracker.assets[asset_str]

                if not asset.tracking_valid:
                    logger.warning(f"Required asset {asset_str} not visible to OptiTrack!")
                    check_passed = False
                    continue

                asset_pos = asset.position.tolist()

                required_pos = self.config['requirements'][asset_type][asset_str]['position']
                for i in range(2):
                    delta_pos = abs(required_pos[i] - asset_pos[i])
                    if delta_pos > POSITION_TOLERANCE:
                        logger.warning(f"Required asset {asset_str} not in the right position!\n \
                                       Required: {required_pos}, found: {asset_pos}")
                        check_passed = False
                        break
                    
                if isinstance(asset, TrackedVisionRobot) and asset_type == "agents":
                    asset_psi = asset.psi

                    required_psi = self.config['requirements'][asset_type][asset_str]['psi']

                    delta_psi = abs(required_psi - asset_psi)
                    delta_psi = float(qmt.wrapToPi(delta_psi))
                    if delta_psi > PSI_TOLERANCE:
                        logger.warning(f"Required agent {asset_str} not correctly turned!\n \
                                       Required: {required_psi}, found: {asset_psi}")
                        check_passed = False
            except Exception as e:
                logger.info(f"Asset {asset_str} not correctly defined: Problem with {e}")

        return check_passed
            

    def loadMovements(self):
        '''Write movement lists to robots'''
        for agent in self.experiment_agents:
            if agent not in self.manager.robots:
                logger.warning(f"Agent {agent} not known to Frodo Manager, skipping {agent} in experiment.")
                continue

            movements_since_last_repeat = []
            if self.config['movement'][agent]['mode'] == 'managed':
                self.manager.robots[agent].setControlMode(3)
                for idx in range(len(self.config['movement'][agent]['movements'])):
                    time.sleep(0.1)
                    movement = self.config['movement'][agent]['movements'][str(idx)]
                    try:
                        if movement['description'] == 'wait':
                            movements_since_last_repeat.append([0,0,movement['time_s']])
                            self.manager.robots[agent].addMovement(dphi=0, radius=0, time=movement['time_s'])
                        elif movement['description'] == 'move':
                            movements_since_last_repeat.append([movement['psi'],movement['radius_mm'],movement['time_s']])
                            self.manager.robots[agent].addMovement(dphi=movement['psi'], radius=movement['radius_mm'],  time=movement['time_s'])
                        elif movement['description'] == 'repeat':
                            for i in range(movement['count']):
                                for move in movements_since_last_repeat:
                                    self.manager.robots[agent].addMovement(dphi=move[0], radius=move[1], time=move[2])
                        else:
                            logger.info(f"Unknown movement description, skipping {movement['description']} of {agent}")
                    except Exception as e:
                        logger.info(f"Problem trying to load movement {idx} of agent {agent}: {e}\nSkipping!")
                        continue

            elif self.config['movement'][agent]['mode'] == "external":
                self.manager.robots[agent].setControlMode(2)
            else:
                self.manager.robots[agent].setControlMode(1)

    def createOutputFolder(self):
        '''Create output folder for experiment.\n
        If already exists: add -index'''
        if not os.path.exists(OUTPUT_FILE_PATH):
            logger.warning(f"Experiment output folder does not exist. \n \
                            Please check if {OUTPUT_FILE_PATH} is at the right location!")
        experiment_name = self.config['id']
        if not os.path.exists(OUTPUT_FILE_PATH + experiment_name):
            self.experiment_name = experiment_name
            self.output_directory_path = OUTPUT_FILE_PATH + experiment_name
            os.mkdir(self.output_directory_path)
            logger.info(f"Created output directory: {OUTPUT_FILE_PATH + experiment_name}")
        else:
            i = 1
            while True:
                if not os.path.exists(OUTPUT_FILE_PATH + experiment_name + "-" + str(i)):
                    break
                i += 1
            self.experiment_name = experiment_name + "-" + str(i)
            self.output_directory_path = OUTPUT_FILE_PATH + self.experiment_name
            os.mkdir(self.output_directory_path)
            logger.info(f"Repition of Experiment {experiment_name}\n \
                        Created output directory: {OUTPUT_FILE_PATH + self.experiment_name}")
        with open(self.output_directory_path + "/" + self.experiment_name + ".json", "w") as file:
            self.config['date'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            json.dump(self.config, file, indent=4)

    def startMovements(self):
        for agent in self.experiment_agents:
            if agent in self.manager.robots:
                self.manager.robots[agent].startNavigationMovement()

    def pauseMovements(self):
        for agent in self.experiment_agents:
            if agent in self.manager.robots:
                self.manager.robots[agent].pauseNavigationMovement()

    def continueMovements(self):
        for agent in self.experiment_agents:
            if agent in self.manager.robots:
                self.manager.robots[agent].continueNavigationMovement()

    def stopExperiment(self):
        for agent in self.experiment_agents:
            if agent in self.manager.robots:
                self.manager.robots[agent].stopNavigationMovement()
                self.manager.robots[agent].clearNavigationMovementQueue()

        self.stopCsvLogging()


    def startExperiment(self, file_name : str):
        self.experiment_agents = []
        with open( INPUT_FILE_PATH + file_name, 'r') as file:
            self.config = json.load(file)
        if self.checkConsistency() and self.checkRequiredPositions():
            self.loadMovements()
            self.createOutputFolder()
            self.start_time = time.time()
            speak(f'Starting Experiment {self.experiment_name}, Time: {humanReadableDate()}')
            self.start_time = time.time()
            self.startCsvLogging()
            self.startMovements()
        logger.info("Finished Experiment Setup, starting!")


class FRODO_Experiments_CLI(CommandSet):

    def __init__(self, experiment_handler: FRODO_ExperimentHandler):
        self.experiment_handler = experiment_handler
        start_experiment_command = Command(name='start', description='Start a new experiment',
                                           callback=self.startExperiment,
                                           arguments=[CommandArgument(name='file',
                                                                      short_name='f',
                                                                      type=str)],
                                                                      allow_positionals=True)

        pause_experiment_command = Command(name='pause', description='Pause the running experiment',
                                           callback=self.pauseExperiment,
                                           arguments=[]
                                           )

        continue_experiment_command = Command(name='continue', description='Continue the paused experiment',
                                           callback=self.continueExperiment,
                                           arguments=[]
                                           )


        stop_experiment_command = Command(name='stop', description='Stop the running experiment',
                                           callback=self.stopExperiment,
                                           arguments=[]
                                           )

        stop_logging_command = Command(name='stopLog', description='Stop running logger',
                                        callback=self.stopLogger,
                                        arguments=[])
        
        logging_marker_command = Command(name='m', description='Audible and visual marker for recognition',
                                         callback=self.markLogger,
                                         arguments=[CommandArgument(name='description',
                                                         short_name='d',
                                                         type=str,
                                                         optional=True,
                                                         default='none',
                                                         description='Marker Description')
                                                    ]
                                        )

        super().__init__(name='experiments', commands=[start_experiment_command,
                                                       pause_experiment_command,
                                                       continue_experiment_command,
                                                       stop_experiment_command,
                                                       stop_logging_command,
                                                       logging_marker_command])

    def startExperiment(self, file):
        self.experiment_handler.startExperiment(file)
        return f"Start Experiment {file}"

    def pauseExperiment(self):
        self.experiment_handler.pauseMovements()

    def continueExperiment(self):
        self.experiment_handler.continueMovements()

    def stopExperiment(self):
        self.experiment_handler.stopExperiment()
    
    def stopLogger(self):
        self.experiment_handler.stopCsvLogging()

    def markLogger(self, description = None):
        playSound('warning')
        self.experiment_handler.markLogger(description)

