from core.device import Device
from robots.bilbo.robot.bilbo_control import BILBO_Control
from robots.bilbo.robot.bilbo_core import BILBO_Core
from robots.bilbo.robot.bilbo_experiment import BILBO_Experiments
from robots.bilbo.robot.bilbo_interfaces import BILBO_Interfaces
from robots.bilbo.robot.bilbo_data import TWIPR_Data, twiprSampleFromDict
from robots.bilbo.robot.bilbo_definitions import *
from robots.bilbo.robot.bilbo_utilities import BILBO_Utilities


# ======================================================================================================================
class BILBO:
    device: Device
    core: BILBO_Core
    control: BILBO_Control
    experiments: BILBO_Experiments

    interfaces: BILBO_Interfaces

    data: TWIPR_Data

    # ==================================================================================================================
    def __init__(self, device: Device, *args, **kwargs):
        self.device = device

        self.core = BILBO_Core(device=device, robot_id=self.device.information.device_id)

        self.control = BILBO_Control(core=self.core)
        self.experiments = BILBO_Experiments(core=self.core)
        self.utilities = BILBO_Utilities(core=self.core)
        self.interfaces = BILBO_Interfaces(core=self.core,
                                           control=self.control,
                                           experiments=self.experiments,
                                           utilities=self.utilities)

        self.data = TWIPR_Data()

        self.device.callbacks.stream.register(self._onStreamCallback)
        self.device.callbacks.disconnected.register(self._disconnected_callback)


    # ------------------------------------------------------------------------------------------------------------------
    def setControlConfiguration(self, config):
        raise NotImplementedError

    # ------------------------------------------------------------------------------------------------------------------
    def loadControlConfiguration(self, name):
        raise NotImplementedError

    # ------------------------------------------------------------------------------------------------------------------
    def saveControlConfiguration(self, name):
        raise NotImplementedError

    #
    #
    # # ------------------------------------------------------------------------------------------------------------------
    # def setSpeed(self, v, psi_dot, *args, **kwargs):
    #     self.device.function('setSpeed', data={'v': v, 'psi_dot': psi_dot})
    #
    # # ------------------------------------------------------------------------------------------------------------------
    # def setBalancingInput(self, torque, *args, **kwargs):
    #     self.device.function('setBalancingInput', data={'input': torque})
    #
    # # ------------------------------------------------------------------------------------------------------------------
    # def setDirectInput(self, left, right, *args, **kwargs):
    #     self.device.function('setDirectInput', data={'left': left, 'right': right})

    # ------------------------------------------------------------------------------------------------------------------


    # === CLASS METHODS =====================================================================

    # === METHODS ============================================================================

    # === PROPERTIES ============================================================================
    @property
    def id(self):
        return self.device.information.device_id

    # === COMMANDS ===========================================================================
    def balance(self, state):
        self.control.setControlMode(BILBO_Control_Mode.BALANCING)

    # ------------------------------------------------------------------------------------------------------------------
    def stop(self):
        self.control.setControlMode(0)

    # ------------------------------------------------------------------------------------------------------------------
    def setLEDs(self, red, green, blue):
        self.device.function('setLEDs', data={'red': red, 'green': green, 'blue': blue})

    # ------------------------------------------------------------------------------------------------------------------
    def _onStreamCallback(self, stream, *args, **kwargs):
        self.data = twiprSampleFromDict(stream.data)

    # ------------------------------------------------------------------------------------------------------------------
    def _disconnected_callback(self, *args, **kwargs):
        del self.experiments

    # ------------------------------------------------------------------------------------------------------------------
    def __del__(self):
        print(f"Deleting {self.id}")
