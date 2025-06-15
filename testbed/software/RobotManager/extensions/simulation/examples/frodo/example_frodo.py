import enum

import extensions.simulation.src.core as core
from extensions.simulation.src.core.environment import BASE_ENVIRONMENT_ACTIONS
from extensions.simulation.src.objects.base_environment import BaseEnvironment
from extensions.simulation.src.objects.frodo import FRODO_DynamicAgent
from core.utils.logging_utils import Logger


class FRODO_ENVIRONMENT_ACTIONS(enum.StrEnum):
    MEASUREMENT = 'frodo_measurement'
    COMMUNICATION = 'frodo_communication'
    ESTIMATION = 'frodo_estimation'


class FrodoEnvironment(BaseEnvironment):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = Logger('FRODO ENV')
        self.logger.setLevel('DEBUG')

        core.scheduling.Action(action_id=FRODO_ENVIRONMENT_ACTIONS.MEASUREMENT,
                               object=self,
                               function=self.action_measurement,
                               priority=31,
                               parent=self.scheduling.actions['objects'])

        core.scheduling.Action(action_id=FRODO_ENVIRONMENT_ACTIONS.COMMUNICATION,
                               object=self,
                               function=self.action_frodo_communication,
                               priority=32,
                               parent=self.scheduling.actions['objects'])

        core.scheduling.Action(action_id=FRODO_ENVIRONMENT_ACTIONS.ESTIMATION,
                               object=self,
                               function=self.action_estimation,
                               priority=33,
                               parent=self.scheduling.actions['objects'])

    def action_measurement(self):
        self.logger.debug(f"{self.scheduling.tick}: Action Frodo Measurement")

    def action_frodo_communication(self):
        self.logger.debug(f"{self.scheduling.tick}: Action Frodo Communication")

    def action_estimation(self):
        self.logger.debug(f"{self.scheduling.tick}: Action Frodo Estimation")


class FRODO_TestAgent(FRODO_DynamicAgent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


        self.logger = Logger(self.agent_id)

        core.scheduling.Action(action_id=FRODO_ENVIRONMENT_ACTIONS.MEASUREMENT,
                               object=self,
                               function=self.action_measurement,
                               priority=1)

        # this prints frodos position and orientation
        self.scheduling.actions[BASE_ENVIRONMENT_ACTIONS.OUTPUT].addAction(self.print_state)

        self.input = [1, 1]

    def action_measurement(self):
        ...

    def print_state(self):
        self.logger.info(f"state: {self.configuration}")

def main():

    Ts = 1
    env = FrodoEnvironment(Ts=Ts, run_mode='rt')

    fr1 = FRODO_TestAgent(agent_id='frodo1v', Ts=Ts)
    env.addObject(fr1)

    env.init()
    fr1.setPosition(3,3)
    print(fr1.getPosition())
    env.start(steps=10)
  

if __name__ == '__main__':

    main()

