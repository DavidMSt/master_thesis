import math
import threading
import time

# === CUSTOM PACKAGES ==================================================================================================
from core.utils.sound.sound import speak
from extensions.cli.src.cli import CommandSet, Command, CommandArgument
from extensions.joystick.joystick_manager import Joystick
from robots.bilbo.robot.bilbo_control import BILBO_Control
from robots.bilbo.robot.bilbo_core import BILBO_Core
from robots.bilbo.robot.bilbo_definitions import BILBO_Control_Mode
from robots.bilbo.robot.bilbo_data import twiprSampleFromDict, BILBO_STATE_DATA_DEFINITIONS
from core.utils.callbacks import CallbackContainer, callback_definition, Callback
from core.utils.events import event_definition, ConditionEvent
from core.utils.exit import register_exit_callback
from robots.bilbo.robot.bilbo_experiment import BILBO_Experiments
from robots.bilbo.robot.bilbo_utilities import BILBO_Utilities

# ======================================================================================================================

JOYSTICK_UPDATE_TIME = 0.05


# ======================================================================================================================
@callback_definition
class BILBO_Interfaces_Callbacks:
    joystick_connected: CallbackContainer
    joystick_disconnected: CallbackContainer


@event_definition
class BILBO_Interfaces_Events:
    joystick_connected: ConditionEvent
    joystick_disconnected: ConditionEvent


# ======================================================================================================================
class BILBO_Interfaces:
    joystick: (Joystick, None)
    live_plots: list[dict]

    joystick_thread: (threading.Thread, None)
    _exit_joystick_thread: bool

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, core: BILBO_Core,
                 control: BILBO_Control,
                 utilities: BILBO_Utilities,
                 experiments: BILBO_Experiments):

        self.core = core
        self.control = control
        self.utilities = utilities
        self.experiments = experiments
        self.core.events.stream.on(self._streamCallback)

        self.cli_command_set = BILBO_CLI_CommandSet(core=self.core,
                                                    control=self.control,
                                                    experiments=self.experiments,
                                                    utilities=self.utilities)

        self.joystick = None
        self.joystick_thread = None

        self._exit_joystick_thread = False

        register_exit_callback(self.close)

    # ------------------------------------------------------------------------------------------------------------------
    def close(self, *args, **kwargs):
        self.removeJoystick()

    # ------------------------------------------------------------------------------------------------------------------
    def addJoystick(self, joystick: Joystick):

        self.core.logger.info("Add Joystick")
        speak(f"Joystick {joystick.id} assigned to {self.core.id}")

        self.joystick = joystick
        self.joystick.events.button.on(self.core.interface_events.resume.set, flags={'button': 'DPAD_RIGHT'},
                                       input_resource=False)
        self.joystick.events.button.on(self.core.interface_events.revert.set, flags={'button': 'DPAD_LEFT'},
                                       input_resource=False)

        self.joystick.events.button.on(Callback(self.control.enableTIC,
                                                inputs={'state': True},
                                                discard_inputs=True), flags={'button': 'DPAD_UP'}, input_resource=False)

        self.joystick.events.button.on(Callback(self.control.enableTIC,
                                                inputs={'state': False},
                                                discard_inputs=True), flags={'button': 'DPAD_DOWN'},
                                       input_resource=False)

        self.joystick.events.button.on(Callback(self.control.setControlMode,
                                                inputs={'mode': BILBO_Control_Mode.BALANCING},
                                                discard_inputs=True),
                                       flags={'button': 'A'}, input_resource=False)

        self.joystick.events.button.on(Callback(self.control.setControlMode,
                                                inputs={'mode': BILBO_Control_Mode.OFF},
                                                discard_inputs=True),
                                       flags={'button': 'B'})

        self.joystick.events.button.on(callback=self.core.beep, flags={'button': 'X'}, input_resource=False)

        self._startJoystickThread()

    # ------------------------------------------------------------------------------------------------------------------
    def removeJoystick(self):
        if self.joystick is not None:
            self.core.logger.info("Remove Joystick")
            speak(f"Joystick {self.joystick.id} removed from {self.core.id}")
            self.joystick.clearAllButtonCallbacks()
            self.joystick = None

        if self.joystick_thread is not None and self.joystick_thread.is_alive():
            self._exit_joystick_thread = True
            self.joystick_thread.join()
            self.joystick_thread = None

    # ------------------------------------------------------------------------------------------------------------------
    def _streamCallback(self, stream, *args, **kwargs):
        data = twiprSampleFromDict(stream.data)
        #
        # for plot in self.live_plots:
        #     state_name = plot["state_name"]
        #     state_data = getattr(data.estimation.state, state_name)
        #     if BILBO_STATE_DATA_DEFINITIONS[state_name]['unit'] == 'rad':
        #         state_data = math.degrees(state_data)
        #     elif BILBO_STATE_DATA_DEFINITIONS[state_name]['unit'] == 'rad/s':
        #         state_data = math.degrees(state_data)
        #     plot["plot"].push_data(state_data)



    # ------------------------------------------------------------------------------------------------------------------
    def _startJoystickThread(self):
        self.joystick_thread = threading.Thread(target=self._joystick_task, daemon=True)
        self.joystick_thread.start()
        self.core.logger.info(
            f"Joystick thread started for {self.core.id}."
        )

    # ------------------------------------------------------------------------------------------------------------------
    def _joystick_task(self):
        self._exit_joystick_thread = False
        while not self._exit_joystick_thread:
            forward_joystick = -self.joystick.getAxis('LEFT_VERTICAL')
            turn_joystick = -self.joystick.getAxis('RIGHT_HORIZONTAL')

            # if self.control.mode == BILBO_Control_Mode.BALANCING:
            self.control.setNormalizedBalancingInput(forward_joystick, turn_joystick)

            time.sleep(JOYSTICK_UPDATE_TIME)


# ======================================================================================================================
class BILBO_CLI_CommandSet(CommandSet):

    def __init__(self, core: BILBO_Core, control: BILBO_Control, experiments: BILBO_Experiments,
                 utilities: BILBO_Utilities):
        self.core = core
        self.control = control
        self.experiments = experiments
        self.utilities = utilities

        beep_command = Command(name='beep',
                               callback=self.core.beep,
                               allow_positionals=True,
                               arguments=[
                                   CommandArgument(name='frequency',
                                                   type=int,
                                                   short_name='f',
                                                   description='Frequency of the beep',
                                                   is_flag=False,
                                                   optional=True,
                                                   default=700),
                                   CommandArgument(name='time_ms',
                                                   type=int,
                                                   short_name='t',
                                                   description='Time of the beep in milliseconds',
                                                   is_flag=False,
                                                   optional=True,
                                                   default=250),
                                   CommandArgument(name='repeats',
                                                   type=int,
                                                   short_name='r',
                                                   description='Number of repeats',
                                                   is_flag=False,
                                                   optional=True,
                                                   default=1)
                               ],
                               description='Beeps the Buzzer')

        speak_command = Command(name='speak',
                                callback=self.core.speak,
                                allow_positionals=True,
                                arguments=[
                                    CommandArgument(name='text',
                                                    type=str,
                                                    short_name='t',
                                                    description='Text to speak',
                                                    is_flag=False,
                                                    optional=True,
                                                    default=None)
                                ], )

        mode_command = Command(name='mode',
                               callback=self.control.setControlMode,
                               allow_positionals=True,
                               arguments=[
                                   CommandArgument(name='mode',
                                                   type=int,
                                                   short_name='m',
                                                   description='Mode of control (0:off, 1:direct, 2:torque)',
                                                   is_flag=False,
                                                   optional=False,
                                                   default=None)
                               ], )

        stop_command = Command(name='stop',
                               callback=Callback(
                                   function=self.control.setControlMode,
                                   inputs={'mode': BILBO_Control_Mode.OFF},
                                   discard_inputs=True,
                               ),
                               description='Deactivates the control on the robot',
                               arguments=[])

        read_state_command = Command(name='read',
                                     callback=self.control.getControlState,
                                     description='Reads the current control state and mode', )

        plot_state_command = Command(name='plot',
                                     callback=self.utilities.openLivePlot,
                                     allow_positionals=True,
                                     arguments=[
                                         CommandArgument(name='state',
                                                         short_name='s',
                                                         type=str,
                                                         description='State to plot',
                                                         optional=False,
                                                         )
                                     ], )

        test_communication = Command(name='testComm',
                                     callback=Callback(
                                         function=self.utilities.test_response_time,
                                         execute_in_thread=True,
                                     ),
                                     description='Tests the communication with the robot',
                                     arguments=[
                                         CommandArgument(name='iterations',
                                                         short_name='i',
                                                         type=int,
                                                         optional=True,
                                                         default=10,
                                                         description='Number of iterations to test')
                                     ])

        statefeedback_command = Command(name='sfg',
                                        callback=self.control.setStateFeedbackGain,
                                        allow_positionals=True,
                                        arguments=[
                                            CommandArgument(name='gain',
                                                            type=list[float],
                                                            array_size=8,
                                                            short_name='g',
                                                            description='State feedback gain',
                                                            )
                                        ], )

        forward_pid_command = Command(name='fpid',
                                      callback=self.control.setForwardPID,
                                      allow_positionals=True,
                                      arguments=[
                                          CommandArgument(name='p',
                                                          type=float,
                                                          short_name='p',
                                                          description='Forward PID P',
                                                          ),
                                          CommandArgument(name='i',
                                                          type=float,
                                                          short_name='i',
                                                          description='Forward PID I',
                                                          ),
                                          CommandArgument(name='d',
                                                          type=float,
                                                          short_name='d',
                                                          description='Forward PID D',
                                                          ),
                                      ], )

        turn_pid_command = Command(name='tpid',
                                   allow_positionals=True,
                                   callback=self.control.setTurnPID,
                                   arguments=[
                                       CommandArgument(name='p',
                                                       type=float,
                                                       short_name='p',
                                                       description='Turn PID P',
                                                       ),
                                       CommandArgument(name='i',
                                                       type=float,
                                                       short_name='i',
                                                       description='Turn PID I',
                                                       ),
                                       CommandArgument(name='d',
                                                       type=float,
                                                       short_name='d',
                                                       description='Turn PID D',
                                                       ),
                                   ])

        read_control_config_command = Command(name='read',
                                              callback=self.control.readControlConfiguration,
                                              description='Reads the current control configuration',
                                              arguments=[])

        control_command_set = CommandSet(name='control', commands=[
            statefeedback_command,
            forward_pid_command,
            turn_pid_command,
            read_control_config_command,
        ])

        test_trajectory_command = Command(name='test',
                                          allow_positionals=True,
                                          callback=self.experiments.runTestTrajectories,
                                          execute_in_thread=True,
                                          arguments=[
                                              CommandArgument(name='num',
                                                              short_name='n',
                                                              type=int,
                                                              description='Number of trajectories',
                                                              optional=False,
                                                              ),
                                              CommandArgument(name='time',
                                                              short_name='t',
                                                              type=float,
                                                              description='Time to run the trajectory',
                                                              optional=False, ),
                                              CommandArgument(name='frequency',
                                                              short_name='f',
                                                              type=float,
                                                              description='Frequency of the Input',
                                                              optional=True,
                                                              default=3),
                                              CommandArgument(name='gain',
                                                              short_name='g',
                                                              type=float,
                                                              description='Gain of the Input',
                                                              optional=True,
                                                              default=0.1),
                                          ])

        experiment_command_set = CommandSet(name='experiment', commands=[test_trajectory_command])

        super().__init__(name=f"{self.core.id}", commands=[beep_command,
                                                           speak_command,
                                                           mode_command,
                                                           stop_command,
                                                           read_state_command,
                                                           plot_state_command,
                                                           test_communication],

                         child_sets=[control_command_set, experiment_command_set])

