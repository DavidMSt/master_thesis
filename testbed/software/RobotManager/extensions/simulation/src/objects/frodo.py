"""
This module defines the simulation world, robot dynamics, physical objects, and agent classes.
It has been refactored so that sample times and model parameters can be provided at construction,
all scheduling actions use the unique "id" field, and robot classes have been renamed:
  - TankRobot -> FRODO
  - TWIPR      -> BILBO

Author: [Your Name]
Date: [Date]
"""

import copy
import dataclasses
import math
import numpy as np
from numpy import nan

from extensions.simulation.src import core as core
from extensions.simulation.src.core.environment import BASE_ENVIRONMENT_ACTIONS

# DEFAULT_SAMPLE_TIME = 0.1


class FRODO_InputSpace(core.spaces.Space):
    """
    Input space for FRODO dynamics.
    Contains scalar dimensions for speed 'v' and steering rate 'psi_dot'.
    """
    dimensions = [
        core.spaces.ScalarDimension(name='v'),
        core.spaces.ScalarDimension(name='psi_dot')
    ]


class FRODO_Spaces(core.dynamics.DynamicsSpaces):
    """
    Collection of spaces for FRODO dynamics.
    """
    input_space = FRODO_InputSpace()
    state_space = core.spaces.Space2D()
    output_space = core.spaces.Space2D()


class FRODO_Dynamics(core.dynamics.Dynamics):
    """
    Continuous-time dynamics for the FRODO robot.
    Updates the 2D position and orientation based on input.
    """

    input_space = FRODO_InputSpace()
    state_space = core.spaces.Space2D()
    output_space = core.spaces.Space2D()

    def init(self):
        pass

    # NOTE: The sample time is now provided via the constructor.
    def __init__(self, Ts, *args, **kwargs):
        self.Ts = Ts
        self.input = self.input_space.getState()
        super().__init__(*args, **kwargs)

    def update(self, input=None):
        if input is not None:
            self.input = input
        self.state = self._dynamics(self.state, self.input)

    def _dynamics(self, state: core.spaces.State, input: core.spaces.State, *args, **kwargs):
        # Update position using current speed and heading.
        state['pos']['x'] = state['pos']['x'] + self.Ts * input['v'] * np.cos(state['psi'].value)
        state['pos']['y'] = state['pos']['y'] + self.Ts * input['v'] * np.sin(state['psi'].value)
        state['psi'] = state['psi'] + self.Ts * input['psi_dot']
        return state

    def _output(self, state: core.spaces.State):
        output = self.output_space.getState()
        output['pos']['x'] = state['pos']['x']
        output['pos']['y'] = state['pos']['y']
        output['psi'] = state['psi']
        return output

    def _init(self, *args, **kwargs):
        pass


class FRODO_PhysicalObject(core.physics.PhysicalBody):
    """
    Physical representation for FRODO.
    Defines dimensions, collision primitives, and proximity sphere.
    """

    def __init__(self, length: float = 0.157, width: float = 0.115, height: float = 0.052, *args, **kwargs):
        super().__init__()
        self.length = length
        self.width = width
        self.height = height
        self.bounding_objects = {
            'body': core.physics.CuboidPrimitive(
                size=[self.length, self.width, self.height],
                position=[0, 0, 0],
                orientation=np.eye(3)
            )
        }
        self.offset = [0, 0, self.height / 2]
        self.proximity_sphere.radius = self._getProximitySphereRadius()

    def update(self, position, orientation, *args, **kwargs):
        self.bounding_objects['body'].position = np.asarray(position) + np.asarray(self.offset)
        self.bounding_objects['body'].orientation = orientation
        self._calcProximitySphere()

    def _calcProximitySphere(self):
        self.proximity_sphere.radius = self._getProximitySphereRadius()
        self.proximity_sphere.update(position=self.bounding_objects['body'].position)

    def _getProximitySphereRadius(self):
        return (np.sqrt(self.length ** 2 + self.width ** 2 + self.height ** 2) / 2) * 1.1


class FRODO_DynamicAgent(core.agents.DynamicAgent):
    object_type: str = 'frodo_agent'
    space = core.spaces.Space2D()
    dynamics: FRODO_Dynamics
    input_space = FRODO_InputSpace()

    def __init__(self, agent_id, Ts, *args, **kwargs):
        self.Ts = Ts
        self.dynamics = FRODO_Dynamics(Ts=Ts)

        super().__init__(agent_id, *args, **kwargs)

        self.scheduling.actions[BASE_ENVIRONMENT_ACTIONS.LOGIC].addAction(self._control)

    @property
    def input(self):
        return self._input

    @input.setter
    def input(self, value):
        self._input = self.input_space.map(value)

    def setPosition(self, x=None, y=None, *args, **kwargs):
        if isinstance(x, list):
            x, y = x[0], x[1]
        super().setPosition([x,y])

    def getPosition(self):
        return [self.configuration_global['pos']['x'], self.configuration_global['pos']['y'] ]

    def getOrientation(self):
        return self.configuration['psi'].value

    def setOrientation(self, psi):
        super().setConfiguration(dimension='psi', value=psi)

    def _control(self):
        self.dynamics.input = self.input


class FRODO_SimObject(core.dynamics.DynamicObject):
    """
    Simulation object for FRODO.
    Combines dynamics and physical representation.
    """
    object_type: str = 'frodo_robot'
    space = core.spaces.Space2D()

    def __init__(self, *args, **kwargs):
        # Set the unique id in the parent class; do not use "name"
        self.id = f"FRODO_{id(self)}"
        # Set robot type (for internal use)
        self.type = 'FRODO'
        self.dynamics = FRODO_Dynamics()
        self.physics: FRODO_PhysicalObject = FRODO_PhysicalObject(*args, **kwargs)
        super().__init__(*args, **kwargs, collision_check=True, collidable=True)

    def _updatePhysics(self, config=None, *args, **kwargs):
        self.physics.update(
            position=[
                self.configuration_global['pos']['x'],
                self.configuration_global['pos']['y'],
                0
            ],
            orientation=self.configuration_global['rot']
        )

    def _getParameters(self):
        params = super()._getParameters()
        params['size'] = {
            'x': self.physics.length,
            'y': self.physics.width,
            'z': self.physics.height
        }
        return params

    def _init(self, *args, **kwargs):
        self._updatePhysics()
