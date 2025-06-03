import dataclasses

import numpy
import qmt

from extensions.optitrack.lib.natnetclient_modified import NatNetClient
# from extensions.optitrack.lib_peter.DataDescriptions import MarkerDescription
from core.utils.callbacks import callback_definition, CallbackContainer
from core.utils.events import event_definition, ConditionEvent
from core.utils.logging_utils import Logger
from core.utils.orientation.orientation_3d import transform_vector_from_a_to_b_frame


# ======================================================================================================================
@dataclasses.dataclass
class RigidBodySample:
    name: str
    id: int
    valid: bool
    position: numpy.ndarray
    orientation: numpy.ndarray
    markers: dict[int, numpy.ndarray]
    markers_raw: dict[int, numpy.ndarray]


# ======================================================================================================================
@dataclasses.dataclass
class MarkerDescription:
    name: str
    id: int
    label: int
    size: (None, float)
    offset: list[float]


# ======================================================================================================================
@dataclasses.dataclass
class RigidBodyDescription:
    name: str
    id: int
    marker_count: int
    markers: dict[int, MarkerDescription]


# ======================================================================================================================
@callback_definition
class OptiTrack_Callbacks:
    sample: CallbackContainer
    description_received: CallbackContainer


# ======================================================================================================================
@event_definition
class OptiTrack_Events:
    sample: ConditionEvent
    description_received: ConditionEvent


# ======================================================================================================================
class OptiTrack:
    callbacks: OptiTrack_Callbacks
    events: OptiTrack_Events
    natnetclient: NatNetClient

    rigid_bodies: dict[str, RigidBodyDescription]

    description_received: bool
    first_data_frame_received: bool

    running: bool

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, server_address):
        self.natnetclient = NatNetClient(server_address)
        self.natnetclient.mocap_data_callback = self._natnet_mocap_data_callback
        self.natnetclient.description_message_callback = self._natnet_description_callback

        self.logger = Logger("Optitrack")
        self.logger.setLevel('INFO')

        self.rigid_bodies = {}
        self.description_received = False
        self.first_data_frame_received = False
        self.running = False

        self.callbacks = OptiTrack_Callbacks()
        self.events = OptiTrack_Events()


    # === METHODS ======================================================================================================

    # ------------------------------------------------------------------------------------------------------------------
    def init(self):
        ...

        # ------------------------------------------------------------------------------------------------------------------


    def start(self):
        try:
            self.natnetclient.run()
        except Exception as e:
            self.logger.error(f"Error while starting NatNetClient. Please make sure that Motive is running")
            return False
        self.logger.info("Start Optitrack")

        return True
        # === PRIVATE METHODS ==============================================================================================


    def _natnet_description_callback(self, data):
        # Rigid Bodies
        for name, rigid_body_data in data["rigid_bodies"].items():
            rigid_body_id = rigid_body_data["id"]
            marker_count = rigid_body_data["marker_count"]
            markers = {}

            for marker_id, marker_description in rigid_body_data["markers"].items():
                marker_offset_y_up = marker_description["offset"]

                # We have to some annoying thing here: Since Optitrack is not changing the marker offset when changing
                # the axis "up"-direction in the streaming pane, we have to manually adjust it to z-up convention.
                # If anyone from the future sees this and they have fixed it: great

                marker_offset = [0.0] * 3
                # marker_offset[0] = marker_offset_y_up[0]
                # marker_offset[1] = -marker_offset_y_up[2]
                # marker_offset[2] = marker_offset_y_up[1]

                marker_offset[0] = -marker_offset_y_up[0]
                marker_offset[1] = -marker_offset_y_up[2]
                marker_offset[2] = marker_offset_y_up[1]

                marker_size = None
                label = self._encode_marker_label(asset_id=rigid_body_id, marker_index=marker_id)
                marker_description = MarkerDescription(id=marker_id,
                                                       offset=marker_offset,
                                                       size=marker_size,
                                                       name='',
                                                       label=label)
                markers[marker_id] = marker_description

            rigid_body_description = RigidBodyDescription(
                name=rigid_body_data["name"],
                id=rigid_body_data["id"],
                marker_count=marker_count,
                markers=markers,
            )

            self.rigid_bodies[rigid_body_data["name"]] = rigid_body_description

        # Marker Sets
        for name, marker_set_data in data['marker_sets'].items():
            ...
            # print(marker_set_data)

        self.description_received = True

        self.callbacks.description_received.call(self.rigid_bodies)
        self.events.description_received.set(self.rigid_bodies)

        # ------------------------------------------------------------------------------------------------------------------


    def _natnet_mocap_data_callback(self, data):
        if not self.description_received:
            return

        if not self.first_data_frame_received:
            self._extract_initial_mocap_information(data)
            self.first_data_frame_received = True
            self.running = True

            self.logger.info(f"Optitrack running!")
            self.logger.info(f"Rigid bodies: {[body.name for body in self.rigid_bodies.values()]}")

        sample = {}

        # Extract the data
        for rigid_body_name, rigid_body_description in self.rigid_bodies.items():
            # Extract the rigid body data
            rbd = data['rigid_bodies'][rigid_body_description.id]
            position = numpy.asarray(rbd['position'])
            orientation_xyzw = rbd['orientation']

            # Change the orientation to our wxyz convention for quaternions
            orientation = numpy.asarray(
                [orientation_xyzw[3], orientation_xyzw[0], orientation_xyzw[1], orientation_xyzw[2]])

            tracking_valid = rbd['tracking_valid']
            marker_error = rbd['marker_error']

            # Extract the raw marker positions
            if rigid_body_name in data['marker_sets']:
                msd = data['marker_sets'][rigid_body_description.name]
            else:
                msd = None

            markers = {}
            markers_raw = {}
            for marker_id, marker_description in rigid_body_description.markers.items():
                marker_index = marker_id

                if msd:
                    marker_position_raw = numpy.asarray(list(msd[marker_index]))
                else:
                    marker_position_raw = None

                marker_position_solved = self._calculate_rigid_body_marker(rigid_body_position=position,
                                                                           rigid_body_orientation=orientation,
                                                                           marker_offset=marker_description.offset)
                markers[marker_id] = marker_position_solved
                markers_raw[marker_id] = marker_position_raw

            rigid_body_sample = RigidBodySample(name=rigid_body_name,
                                                id=rigid_body_description.id,
                                                valid=tracking_valid,
                                                position=position,
                                                orientation=orientation,
                                                markers=markers,
                                                markers_raw=markers_raw)

            sample[rigid_body_name] = rigid_body_sample

        for callback in self.callbacks.sample:
            callback(sample)

        self.events.sample.set(resource=sample)

        # ------------------------------------------------------------------------------------------------------------------


    def _extract_initial_mocap_information(self, data):
        for rigid_body_id, rigid_body_description in self.rigid_bodies.items():
            for marker_id, marker_description in rigid_body_description.markers.items():
                if marker_description.label in data['labeled_markers']:
                    marker_size = data['labeled_markers'][marker_description.label]['size'][0]
                    marker_description.size = marker_size
                else:
                    self.logger.warning(f"Marker {marker_id} of rigid body \"{rigid_body_id}\" currently not visible. "
                                   f"It's size will be inferred from the other markers.")

            # loop again through the markers and check the ones that have not been set yet
            for marker_id, marker_description in rigid_body_description.markers.items():
                if marker_description.size is None:
                    # Calculate the mean over all markers where the size if not None
                    sizes = [marker_description.size for marker_description in rigid_body_description.markers.values()
                             if marker_description.size is not None]

                    if len(sizes) == 0:
                        self.logger.error(f"No markers of rigid body {rigid_body_id} are visible")
                        marker_description.size = 0
                    else:
                        marker_description.size = sum(sizes) / len(sizes)

        # ------------------------------------------------------------------------------------------------------------------


    @staticmethod
    def _encode_marker_label(asset_id, marker_index):
        """
        Encode an asset id and a marker index into a single marker id.

        The marker id is computed by shifting the asset id left by 16 bits and then adding the marker index.

        Parameters:
          asset_id (int): The asset identifier (e.g., 500, 501, etc.).
          marker_index (int): The marker index (e.g., 1, 2, 3, ...).

        Returns:
          int: The encoded marker id.
        """
        return (asset_id << 16) + marker_index


    @staticmethod
    def _decode_marker_label(marker_id):
        """
        Decode a marker id into its asset id and marker index components.

        Given a marker id that was computed as:

            marker_id = (asset_id << 16) + marker_index

        This function returns the original asset id and marker index.

        Parameters:
          marker_id (int): The full marker id.

        Returns:
          tuple: A tuple (asset_id, marker_index).
        """
        asset_id = marker_id >> 16
        marker_index = marker_id & 0xFFFF  # 0xFFFF == 65535, gets the lower 16 bits
        return asset_id, marker_index


    @staticmethod
    def _calculate_rigid_body_marker(rigid_body_position, rigid_body_orientation, marker_offset):
        marker_offset = numpy.asarray(marker_offset)

        q = qmt.qinv(rigid_body_orientation)
        vector_rotated = transform_vector_from_a_to_b_frame(vector_in_a_frame=marker_offset,
                                                            orientation_from_b_to_a=rigid_body_orientation)

        vector_out = vector_rotated + rigid_body_position

        return vector_out
