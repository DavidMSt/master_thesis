import time

from applications.FRODO.tracker.assets import TrackedAsset, vision_robot_application_assets
from extensions.optitrack.optitrack import OptiTrack, RigidBodySample
from core.utils.callbacks import callback_definition, CallbackContainer
from core.utils.events import event_definition, ConditionEvent
from core.utils.logging_utils import Logger

# =====================================================================================================================
logger = Logger('Tracker')
logger.setLevel('INFO')


@callback_definition
class Tracker_Callbacks:
    """
    Container for tracker callback events.
    """
    new_sample: CallbackContainer  # Called when a new sample is received
    description_received: CallbackContainer  # Called when a description is received from OptiTrack


@event_definition
class Tracker_Events:
    """
    Container for tracker event handling.
    """
    new_sample: ConditionEvent  # Event triggered on new sample reception
    description_received: ConditionEvent  # Event triggered on receiving asset descriptions


# =====================================================================================================================
class Tracker:
    """
    Main Tracker class responsible for handling assets tracking using OptiTrack.
    """
    assets: dict[str, TrackedAsset]  # Dictionary of tracked assets
    tracked_assets: dict[str, TrackedAsset]
    optitrack: OptiTrack  # OptiTrack instance for motion tracking

    callbacks: Tracker_Callbacks  # Callback handler
    events: Tracker_Events  # Event handler

    # === INIT =========================================================================================================
    def __init__(self, assets: dict[str, TrackedAsset] = vision_robot_application_assets):
        """
        Initializes the Tracker instance.
        :param assets: Dictionary of assets to be tracked, default is vision_robot_application_assets.
        """
        self.assets = assets
        self.optitrack = OptiTrack(server_address="192.168.8.248")  # Initialize OptiTrack with server address

        self.optitrack.logger.switchLoggingLevel('INFO','DEBUG')
        self.optitrack.logger.setLevel('DEBUG')

        self.tracked_assets = {}

        # Set up an event listener for new samples
        self.optitrack.events.sample.on(self._optitrack_new_sample_callback, input_resource=True)

        # Register callback for description reception
        self.optitrack.callbacks.description_received.register(self._optitrack_description_callback)

        self.callbacks = Tracker_Callbacks()
        self.events = Tracker_Events()

    # ------------------------------------------------------------------------------------------------------------------
    def init(self):
        """
        Initializes the OptiTrack system.
        """
        self.optitrack.init()

    # ------------------------------------------------------------------------------------------------------------------
    def start(self):
        """
        Starts the tracking system. Returns False if OptiTrack fails to start.
        """
        success = self.optitrack.start()

        if not success:
            logger.error("Could not start OptiTrack. Tracking disabled")
            return False

        logger.info("Starting Tracker")

        return True
        # self.event_listener_sample.start()  # Start the event listener for new samples
        # self._thread.start()  # Uncomment if background thread processing is needed

    # === PRIVATE METHODS ==============================================================================================
    def _optitrack_new_sample_callback(self, sample: dict[str, RigidBodySample], *args, **kwargs):
        """
        Callback function triggered when a new sample is received from OptiTrack.
        :param sample: Dictionary containing rigid body samples.
        """
        for name, asset in self.tracked_assets.items():
            # Ensure asset data exists in the sample
            if name not in sample:
                logger.error(f"Tracked asset {name} not found in sample")
                continue

            asset_data = sample[name]  # Retrieve asset data
            asset.update(asset_data)  # Update asset state

        self.callbacks.new_sample.call(self.tracked_assets)  # Trigger callback
        self.events.new_sample.set(self.tracked_assets)  # Set event

    # ------------------------------------------------------------------------------------------------------------------
    def _optitrack_description_callback(self, rigid_bodies):
        """
        Callback function triggered when OptiTrack sends a description update.
        :param rigid_bodies: Dictionary containing OptiTrack rigid body descriptions.
        """
        all_assets_tracked = True

        # Check if all assets are currently tracked
        for name, asset in self.assets.items():
            if name not in rigid_bodies:
                logger.debug(f"Asset {name} not available in OptiTrack data")
                all_assets_tracked = False
            else:
                self.tracked_assets[name] = asset  # Update tracked assets dictionary

        if all_assets_tracked:
            logger.info("All assets tracked")

        logger.info(f"Tracked assets: {list(self.tracked_assets.keys())}")

        self.callbacks.description_received.call(self.tracked_assets)  # Trigger callback
        self.events.description_received.set(self.tracked_assets)  # Set event


# =====================================================================================================================
if __name__ == '__main__':
    """
    Main execution block for running the Tracker.
    """
    tracker = Tracker()
    tracker.init()
    tracker.start()

    while True:
        time.sleep(1)  # Keep the script running