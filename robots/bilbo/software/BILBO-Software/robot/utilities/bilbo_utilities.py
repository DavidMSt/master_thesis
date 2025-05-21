from robot.communication.bilbo_communication import BILBO_Communication
from robot.hardware import get_hardware_definition
from core.utils.events import event_definition, ConditionEvent
from core.utils.sound.sound import SoundSystem


@event_definition
class BILBO_Utilities_Events:
    resume: ConditionEvent


# ======================================================================================================================
class BILBO_Utilities:
    sound_system: SoundSystem

    def __init__(self, communication: BILBO_Communication):
        hardware_definition = get_hardware_definition()

        if hardware_definition['electronics']['sound']['active']:
            self.sound_system = SoundSystem(hardware_definition['electronics']['sound']['gain'] * 0.2)
        else:
            self.sound_system = None

        self.communication = communication
        self.events = BILBO_Utilities_Events()

        self.communication.wifi.addCommand(
            identifier='speak',
            callback=self.speak,
            arguments=['message'],
            description='Speak the given message'
        )

        self.communication.wifi.addCommand(
            identifier='resume',
            callback=self.resume,
            arguments=[],
            description='Resume the robot'
        )

    # ------------------------------------------------------------------------------------------------------------------
    def init(self):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def start(self):
        if self.sound_system is not None:
            self.sound_system.start()

    # ------------------------------------------------------------------------------------------------------------------
    def playTone(self, tone):
        if self.sound_system is None:
            return
        self.sound_system.play(tone)

    # ------------------------------------------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------------------
    def speak(self, message, on_host=True):
        # if self.sound_system is None:
        #     if on_host:
        #         self.communication.wifi.sendEvent(event='speak',
        #                                           data={
        #                                               'message': message,
        #                                           })
        # self.sound_system.speak(message)
        self.communication.wifi.sendEvent(event='speak',
                                          data={
                                              'message': message,
                                          })

    # ------------------------------------------------------------------------------------------------------------------
    def resume(self):
        self.events.resume.set()
