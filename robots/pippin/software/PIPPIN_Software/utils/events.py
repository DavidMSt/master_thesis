import threading
from copy import copy
from threading import Lock, Condition, Event
from utils.callbacks import Callback


# ======================================================================================================================
class SharedResource:
    def __init__(self, resource=None):
        self.lock = Lock()
        self.resource = resource

    def acquire(self):
        self.lock.acquire()

    def release(self):
        self.lock.release()

    def set(self, value):
        self.lock.acquire()
        self.resource = value
        self.lock.release()

    def get(self):
        output = self.resource
        return output

    def __enter__(self):
        self.lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()


# ======================================================================================================================


# ======================================================================================================================
class ConditionEvent(Condition):
    resource: SharedResource
    flag: (str, None)

    # is_set: bool = False

    def __init__(self):
        super().__init__()
        self.resource = SharedResource()
        self.flag = None
        # self.is_set = False

    def set(self, resource=None, flag=None):
        """
        Notify all waiting threads and optionally update the shared resource.
        """
        # assert (is_immutable(resource) or resource is None)
        with self:
            self.flag = flag
            self.resource.set(resource)
            # self.is_set = True
            self.notify_all()

    def wait(self, timeout=None):
        """
        Wait for the condition to be notified, inheriting behavior from the base class.

        :param timeout: Optional timeout for the wait.
        """
        with self:
            # if self.is_set:
            #     return True
            return super().wait(timeout)

    def wait_for(self, predicate, timeout=None):
        with self:
            return super().wait_for(predicate, timeout)

    def get_data(self):
        """
        Access the shared resource.
        """
        with self.resource:
            return self.resource.get()

    def clear_data(self):
        """
        Clear the shared resource if needed.
        """
        with self:
            self.resource.acquire()
            self.resource.set(None)
            self.resource.release()


# ======================================================================================================================
class EventListener:
    def __init__(self, event: ConditionEvent, callback, once=False, finished_callback=None):
        """
        Initializes the EventListener.

        :param event: The event to listen for (threading.Event or threading.Condition).
        :param callback: The callback function to execute when the event is triggered.
        :param once: If True, the listener will stop after one execution.
        :param finished_callback: Optional callback to execute after the main callback is done.
        """
        assert (isinstance(event, ConditionEvent))

        self.event = event
        self.kill_event = threading.Event()

        self._event = event or self.kill_event
        self.callback = callback
        self.once = once
        self.finished_callback = finished_callback
        self._running = True  # Flag to control the listener thread
        self.thread = threading.Thread(target=self._listen)
        self.thread.daemon = True

    def _listen(self):
        while self._running:
            with self._event:
                self._event.wait()  # Wait for the condition to be notified
                if not self.kill_event.is_set():
                    self._execute_callback()
            if self.once:
                break  # Exit the loop if we only listen once

    def _execute_callback(self):
        try:
            self.callback(self._event.get_data())  # Execute the main callback
        finally:
            if self.finished_callback:
                self.finished_callback(self._event.get_data())  # Execute the finished callback, if provided

    def start(self):
        """Starts the listener thread."""
        self.thread.start()

    def stop(self):
        """Stops the listener thread."""
        self._running = False
        self.kill_event.set()
        self.thread.join()


# ======================================================================================================================
def event_handler(cls):
    """
    Decorator to make ConditionEvent fields independent for each instance.
    """
    original_init = cls.__init__

    def new_init(self, *args, **kwargs):
        # Call the original __init__ method
        if original_init:
            original_init(self, *args, **kwargs)

        # Replace all class-level ConditionEvent attributes with instance-level ones
        for attr_name, attr_value in cls.__annotations__.items():
            if attr_value is ConditionEvent:
                setattr(self, attr_name, ConditionEvent())

    cls.__init__ = new_init
    return cls
