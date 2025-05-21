import enum
import threading
import time


def disableLibcameraLogs():
    import os
    os.environ["LIBCAMERA_LOG_LEVELS"] = "*:4"


disableLibcameraLogs()

import cv2
from libcamera import controls
from picamera2 import picamera2
from video_streamer import VideoStreamer
from utils.logging_utils import Logger

# ======================================================================================================================
logger = Logger("PyCamera")
logger.setLevel('DEBUG')


class PyCameraType(enum.Enum):
    V1 = 1,
    V2 = 2,
    V3 = 3,


# ======================================================================================================================
class PyCamera:
    picam: picamera2.Picamera2
    resolution: tuple
    version: PyCameraType
    running: bool = False
    _camera_lock: threading.Lock

    def __init__(self, version: PyCameraType, resolution: tuple, auto_focus: bool = False):

        self.version = version
        self.resolution = resolution

        self.picam = picamera2.Picamera2()

        if self.version == PyCameraType.V2:
            self.picam_config = self.picam.create_video_configuration(raw={"size": (1640, 1232)},
                                                                      main={"format": "RGB888", "size": resolution},
                                                                      buffer_count=5)
        elif self.version == PyCameraType.V3:
            self.picam_config = self.picam.create_video_configuration(raw={"size": (2304, 1296)},
                                                                      main={"format": "RGB888", "size": resolution},
                                                                      buffer_count=5)
        elif self.version == PyCameraType.V1:
            self.picam_config = self.picam.create_video_configuration(raw={"size": (2592, 1944)},
                                                                      main={"format": "RGB888", "size": resolution},
                                                                      buffer_count=5)

        self.picam.configure(self.picam_config)

        if auto_focus:
            self.picam.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        self._camera_lock = threading.Lock()

    # === METHODS ======================================================================================================
    def init(self):
        ...

    def start(self):
        self.running = True
        self.picam.start()
        logger.info("PyCamera started!")

    def takeFrame(self):
        with self._camera_lock:
            return self.picam.capture_array()

    @staticmethod
    def getImageBuffer(frame):
        _, buffer = cv2.imencode('.jpg', frame)
        return buffer

    def getImageBufferBytes(self, frame):
        return self.getImageBuffer(frame).tobytes()


# ======================================================================================================================
class PyCameraStreamer(VideoStreamer):
    pycamera: PyCamera

    def __init__(self, pycamera: PyCamera = None, resolution: tuple = None):
        super().__init__()

        if pycamera is None:
            if resolution is None:
                resolution = (960, 540)
            # self.camera = PyCamera(PyCameraType.V1, resolution, auto_focus=True)
            self.camera = PyCamera(PyCameraType.V1, resolution, auto_focus=False)
        else:
            self.camera = pycamera

        self.image_fetcher = self.getCameraFrame

    def start(self):
        if not self.camera.running:
            self.camera.start()

        super().start()

    def getCameraFrame(self):
        frame = self.camera.takeFrame()
        return self.camera.getImageBufferBytes(frame)


if __name__ == '__main__':
    streamer = PyCameraStreamer()
    streamer.start()
    while True:
        time.sleep(10)
