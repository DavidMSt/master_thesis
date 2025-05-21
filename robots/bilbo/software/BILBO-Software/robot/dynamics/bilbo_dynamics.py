import json

from control import tf

from core.utils.files import fileExists
from paths import calibrations_path


class BILBO_Dynamics:
    transfer_function: tf

    def __init__(self):
        self.transfer_function = tf()

        # Check if there is a file with dat in it
        if fileExists(f"{(calibrations_path / 'system_dynamics.json')}"):
            data = json.load(f"{(calibrations_path / 'system_dynamics.json')}")

    def getTransitionMatrix(self, N: int):
        ...

    def runIdentification(self):
        ...
