from typing import Any

from core.utils.callbacks import callback_definition, CallbackContainer
from core.utils.colors import rgb_to_hex
from core.utils.logging_utils import Logger
from extensions.control_gui.src.lib.objects import GUI_Object


# === BUTTON ===========================================================================================================
@callback_definition
class ButtonCallbacks:
    click: CallbackContainer
    doubleClick: CallbackContainer
    longClick: CallbackContainer
    rightClick: CallbackContainer


class Button(GUI_Object):
    type = 'button'
    text: str
    config: dict

    callbacks: ButtonCallbacks

    # === INIT =========================================================================================================
    def __init__(self, id: str, text=None, config=None):
        super().__init__(id)

        self.text = text if text is not None else id

        default_config = {
            'text': '',
            'color': [0.2, 0.2, 0.2],
            'textColor': [1, 1, 1, 0.8],
            'fontSize': 12,
        }

        self.logger = Logger(f"Button {self.id}", 'DEBUG')
        self.callbacks = ButtonCallbacks()

        self.config = {**default_config, **config}

        if text is not None:
            self.config['text'] = text

    # === METHODS ======================================================================================================
    def getConfiguration(self) -> dict:
        config = {
            'type': self.type,
            'id': self.uid,
            **self.config,
        }

        return config

    # ------------------------------------------------------------------------------------------------------------------
    def getData(self) -> dict:
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def onMessage(self, message) -> Any:
        if message['event'] == 'click':
            self.logger.debug(f"Button {self.uid} clicked")
            for callback in self.callbacks.click:
                callback(button=self)
        elif message['event'] == 'doubleClick':
            self.logger.debug(f"Button {self.uid} double clicked")
            for callback in self.callbacks.doubleClick:
                callback(button=self)
        elif message['event'] == 'longClick':
            self.logger.debug(f"Button {self.uid} long clicked")
            for callback in self.callbacks.longClick:
                callback(button=self)
        elif message['event'] == 'rightClick':
            self.logger.debug(f"Button {self.uid} right clicked")
            for callback in self.callbacks.rightClick:
                callback(button=self)

    # ------------------------------------------------------------------------------------------------------------------
    def init(self, *args, **kwargs):
        pass


# === MULTI-STATE BUTTON ===============================================================================================
@callback_definition
class MultiStateButtonCallbacks:
    click: CallbackContainer
    doubleClick: CallbackContainer
    longClick: CallbackContainer
    rightClick: CallbackContainer
    indicatorClick: CallbackContainer
    state: CallbackContainer


class MultiStateButton(GUI_Object):
    type: str = 'multi_state_button'

    callbacks: MultiStateButtonCallbacks

    config: dict
    states: list[str]
    state: str

    _state_index: int

    # === INIT =========================================================================================================
    def __init__(self, id, states, current_state=None, config=None, **kwargs):
        super().__init__(id)

        default_config = {
            'color': [0.2, 0.2, 0.2],
            'textColor': [1, 1, 1, 0.8],
            'fontSize': 12,
        }

        self.config = {**default_config, **(config or {}), **kwargs}

        # Check the color array. It can be an array of arrays, but then it has to have the same length as the states
        if isinstance(self.config['color'], list) and all(isinstance(color, list) for color in self.config['color']):
            if not len([color for color in self.config['color']]) == len(states):
                raise ValueError("The color array has to have the same length as the states")

        self.logger = Logger(f"MultiStateButton {self.id}", 'DEBUG')
        self.callbacks = MultiStateButtonCallbacks()

        self.states = states

        # Check if all states are strings and different from each other
        if not all(isinstance(state, str) for state in states):
            raise ValueError("All states must be strings")
        if len(states) != len(set(states)):
            raise ValueError("All states must be unique")

        if isinstance(current_state, int):
            self._state_index = current_state
        elif isinstance(current_state, str):
            self._state_index = self.states.index(current_state)
        else:
            self._state_index = 0

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def state(self):
        return self.states[self._state_index]

    # ------------------------------------------------------------------------------------------------------------------
    @state.setter
    def state(self, value):
        if value not in self.states:
            raise ValueError(f"State '{value}' not found in states")

        if value == self.state:
            return

        self._state_index = self.states.index(value)
        self.logger.debug(f"Setting state to {value}")
        for callback in self.callbacks.state:
            callback(button=self, state=value, index=self.state_index)
        self.update()

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def state_index(self):
        return self._state_index

    # ------------------------------------------------------------------------------------------------------------------
    @state_index.setter
    def state_index(self, value):
        value = value % len(self.states)

        if value == self.state_index:
            return

        self._state_index = value
        self.logger.debug(f"Setting state index to {value}")
        for callback in self.callbacks.state:
            callback(button=self, state=self.state, index=self.state_index)

        self.update()
    # ------------------------------------------------------------------------------------------------------------------
    def getConfiguration(self) -> dict:
        configuration = {
            'type': self.type,
            'id': self.uid,
            'states': self.states,
            'state': self.state,
            'state_index': self.state_index,
            **self.config,
        }
        return configuration

    # ------------------------------------------------------------------------------------------------------------------
    def onMessage(self, message) -> Any:
        self.logger.debug(f"Received message: {message}")
        match message['event']:
            case 'click':
                self.state_index = (self.state_index + 1) % len(self.states)
                for callback in self.callbacks.click:
                    callback(button=self, state=self.state, index=self.state_index)
            case 'rightClick':
                self.state_index = (self.state_index - 1) % len(self.states)
                for callback in self.callbacks.rightClick:
                    callback(button=self, state=self.state, index=self.state_index)
            case 'indicatorClick':
                index = message['data']['index']
                self.state_index = index % len(self.states)
                for callback in self.callbacks.indicatorClick:
                    callback(button=self, state=self.state, index=self.state_index)

    # ------------------------------------------------------------------------------------------------------------------
    def init(self, *args, **kwargs):
        pass
