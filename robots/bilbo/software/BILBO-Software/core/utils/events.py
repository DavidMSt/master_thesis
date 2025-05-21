# import threading
# import time
# from threading import Lock, Condition
# import weakref
# import collections
#
# # ======================================================================================================================
# class SharedResource:
#     def __init__(self, resource=None):
#         self.lock = Lock()
#         self.resource = resource
#
#     def acquire(self):
#         self.lock.acquire()
#
#     def release(self):
#         self.lock.release()
#
#     def set(self, value):
#         with self.lock:
#             self.resource = value
#
#     def get(self):
#         return self.resource
#
#     def __enter__(self):
#         self.lock.acquire()
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self.lock.release()
#
#
# class ConditionEvent(threading.Condition):
#     id: str
#     resource: 'SharedResource'
#     flag: any
#     _parameters_def: list
#
#     def __init__(self, flags=None, history_size=10, id=None):
#         """
#         :param flags: Optional list of tuples, e.g. [('param1', str), ('param2', type)]
#                       which defines the allowed parameters for the event.
#         :param history_size: The maximum number of historical events to store.
#         :param id: Optional identifier for the event. If not provided explicitly, the event_handler
#                    decorator will set the id to the attribute name.
#         """
#         super().__init__()
#         self.id = id
#         self.resource = SharedResource()
#         self.flag = None
#         self._parameters_def = flags if flags is not None else []
#         self._last_set_time = None
#         # List of listeners. Each listener is a tuple: (callback_ref, flags, once)
#         self._listeners = []
#         # Deque to store history events as tuples: (timestamp, flags)
#         self._event_history = collections.deque(maxlen=history_size)
#
#     def on(self, callback, flags=None, once=False, input_resource=False):
#         """
#         Register a callback to be called once the event is set and the flags match.
#         The callback will be executed in a separate oneshot thread with the event's resource data.
#         """
#         try:
#             if hasattr(callback, '__self__') and callback.__self__ is not None:
#                 callback_ref = weakref.WeakMethod(callback)
#             else:
#                 callback_ref = callback
#         except Exception:
#             callback_ref = callback
#
#         with self:
#             self._listeners.append((callback_ref, flags, once, input_resource))
#
#     def set(self, resource=None, flags=None):
#         """
#         Notify all waiting threads and optionally update the shared resource.
#         Also triggers any registered listener callbacks if their filtering flags match.
#         """
#         with self:
#             if self._parameters_def:
#                 # Validate provided flags if parameters are defined.
#                 if flags is not None:
#                     if not isinstance(flags, dict):
#                         raise ValueError("Flag must be provided as a dictionary if provided with parameters: {}".format(
#                             self._parameters_def))
#                     allowed_keys = {p[0] for p in self._parameters_def}
#                     for key, value in flags.items():
#                         if key not in allowed_keys:
#                             raise ValueError("Unexpected parameter: {}".format(key))
#                         for param_name, param_type in self._parameters_def:
#                             if key == param_name:
#                                 # Allow the flag value to be a list or tuple of allowed types.
#                                 if isinstance(value, (list, tuple)):
#                                     if not all(isinstance(v, param_type) for v in value):
#                                         raise TypeError(
#                                             "Each item for parameter '{}' must be of type {}".format(key, param_type))
#                                 elif not isinstance(value, param_type):
#                                     raise TypeError("Parameter '{}' must be of type {}".format(key, param_type))
#             self.flag = flags
#             self.resource.set(resource)
#             timestamp = time.time()
#             self._last_set_time = timestamp
#             self._event_history.append((timestamp, self.flag))
#             self.notify_all()
#
#             # Process listeners.
#             to_call = []
#             remaining_listeners = []
#             for callback_ref, listener_flags, once_flag in self._listeners:
#                 if self._check_flag(listener_flags):
#                     to_call.append(callback_ref)
#                     if not once_flag:
#                         remaining_listeners.append((callback_ref, listener_flags, once_flag))
#                 else:
#                     remaining_listeners.append((callback_ref, listener_flags, once_flag))
#             self._listeners = remaining_listeners
#
#         for callback_ref in to_call:
#             # Always resolve weak references to get the actual callback.
#             if isinstance(callback_ref, weakref.WeakMethod):
#                 callback_func = callback_ref()
#             else:
#                 callback_func = callback_ref
#             if callback_func is None:
#                 continue
#             threading.Thread(target=self._call_listener, args=(callback_func,)).start()
#
#     def _call_listener(self, callback):
#         try:
#             data = self.get_data()
#             callback(data)
#         except Exception as e:
#             print("Error in listener callback:", e)
#
#     # def _check_flag(self, filter_params):
#     #     """
#     #     Check if the current flag matches the filtering parameters.
#     #     """
#     #     if not filter_params:
#     #         return True
#     #     if not isinstance(self.flag, dict):
#     #         return False
#     #     for key, condition in filter_params.items():
#     #         if key not in self.flag:
#     #             return False
#     #         actual = self.flag[key]
#     #         if isinstance(condition, (list, tuple, set)):
#     #             if actual not in condition:
#     #                 return False
#     #         elif callable(condition):
#     #             if not condition(actual):
#     #                 return False
#     #         else:
#     #             if actual != condition:
#     #                 return False
#     #     return True
#     def _check_flag(self, filter_params):
#         if not filter_params:
#             return True
#         if not isinstance(self.flag, dict):
#             return False
#         for key, condition in filter_params.items():
#             if key not in self.flag:
#                 return False
#             actual = self.flag[key]
#
#             # Handle if the actual flag is a list/tuple/set.
#             if isinstance(actual, (list, tuple, set)):
#                 # If listener condition is also a collection, check for any intersection.
#                 if isinstance(condition, (list, tuple, set)):
#                     if not set(actual).intersection(condition):
#                         return False
#                 else:
#                     if condition not in actual:
#                         return False
#             else:
#                 # actual is not a collection
#                 if isinstance(condition, (list, tuple, set)):
#                     if actual not in condition:
#                         return False
#                 elif callable(condition):
#                     if not condition(actual):
#                         return False
#                 else:
#                     if actual != condition:
#                         return False
#         return True
#
#     def _match_flags(self, event_flags, conditions):
#         """
#         Check if the provided event_flags match the filtering conditions.
#         """
#         if not conditions:
#             return True
#         if not isinstance(event_flags, dict):
#             return False
#         for key, condition in conditions.items():
#             if key not in event_flags:
#                 return False
#             actual = event_flags[key]
#             if isinstance(condition, (list, tuple, set)):
#                 if actual not in condition:
#                     return False
#             elif callable(condition):
#                 if not condition(actual):
#                     return False
#             else:
#                 if actual != condition:
#                     return False
#         return True
#
#     def wait(self, timeout=None, stale_event_time=None, flags: dict = None, resource_filter=None, **filter_params):
#         """
#         Wait for the condition to be notified and for the flags to match the given criteria.
#         Additionally, if stale_event_time is provided, check if an event was set within that time.
#         Additionally, if resource_filter is provided, check if the event's resource satisfies the given condition.
#         For example, if the resource is a dict, you can wait until a given key has a specific value.
#         If the resource is not shaped as assumed by resource_filter, the check safely fails.
#
#         :param timeout: Optional timeout for the wait.
#         :param stale_event_time: Optional duration (in seconds) within which a recent event (with matching flags)
#                                  will immediately satisfy the wait.
#         :param flags: Optional dict of flags to filter event parameters.
#         :param resource_filter: Optional filter to apply to the resource. If a dict, each key-value pair is compared
#                                 against the resource (if it is a dict). Otherwise, a simple equality check is performed.
#         :param filter_params: Additional key-value pairs to filter event parameters.
#         :return: True if the condition was met, False if the wait timed out.
#         """
#         def _check_resource(data, resource_filter):
#             try:
#                 if isinstance(resource_filter, dict) and isinstance(data, dict):
#                     for key, value in resource_filter.items():
#                         if data.get(key) != value:
#                             return False
#                     return True
#                 else:
#                     return data == resource_filter
#             except Exception:
#                 return False
#
#         with self:
#             # Merge filtering conditions.
#             conditions = {}
#             if flags:
#                 conditions.update(flags)
#             if filter_params:
#                 conditions.update(filter_params)
#
#             # Check event history for a recent event that matches the conditions.
#             if stale_event_time is not None:
#                 now = time.time()
#                 for ts, event_flags in self._event_history:
#                     if now - ts <= stale_event_time and self._match_flags(event_flags, conditions):
#                         if resource_filter is not None:
#                             data = self.get_data()
#                             if _check_resource(data, resource_filter):
#                                 return True
#                         else:
#                             return True
#
#             end_time = time.time() + timeout if timeout is not None else None
#
#             while True:
#                 remaining = end_time - time.time() if end_time is not None else None
#                 if remaining is not None and remaining <= 0:
#                     return False
#                 super().wait(remaining)
#                 if self._check_flag(conditions):
#                     if resource_filter is not None:
#                         data = self.get_data()
#                         if _check_resource(data, resource_filter):
#                             return True
#                     else:
#                         return True
#
#     def get_data(self):
#         with self.resource:
#             return self.resource.get()
#
#     def clear_data(self):
#         with self:
#             self.resource.acquire()
#             self.resource.set(None)
#             self.resource.release()
#
#     def reset(self):
#         with self:
#             self.flag = None
#             self._last_set_time = None
#             self.resource.set(None)
#
#
# def waitForEvents(events: list, timeout=None, wait_for_all=False):
#     """
#     Wait for one or more events with corresponding flag conditions.
#
#     :param events: A list of tuples (event, flags), where 'flags' is a dictionary used to filter event parameters.
#                    Example: [(event1, {'value1': 2}), (event2, {'value33': 'hello'}), (event3, None)]
#     :param timeout: Overall timeout in seconds.
#     :param wait_for_all: If False, returns as soon as one event is triggered with matching flags;
#                          if True, waits until all events are triggered with matching flags.
#     :return: If wait_for_all is False, returns the first event that meets its flags.
#              If wait_for_all is True, returns a list of events in the same order as provided.
#              Returns None if the timeout expires.
#     """
#     results = []
#     lock = threading.Lock()
#     done_event = threading.Event()
#     threads = []
#     start_time = time.time()
#
#
#
#     for i,value in enumerate(events):
#         if isinstance(value, ConditionEvent):
#             events[i] = (value, None)
#
#     def worker(ev, flags, overall_timeout):
#         remaining = overall_timeout - (time.time() - start_time) if overall_timeout is not None else None
#         if remaining is not None and remaining <= 0:
#             return
#         ret = ev.wait(timeout=remaining, flags=flags)
#         if ret:
#             with lock:
#                 results.append(ev)
#             if not wait_for_all:
#                 done_event.set()
#
#     # Start a thread for each event.
#     for ev, flags in events:
#         t = threading.Thread(target=worker, args=(ev, flags, timeout))
#         t.daemon = True
#         t.start()
#         threads.append(t)
#
#     if wait_for_all:
#         # Wait for all threads to finish, taking into account the overall timeout.
#         for t in threads:
#             remaining = timeout - (time.time() - start_time) if timeout is not None else None
#             t.join(timeout=remaining)
#         if len(results) == len(events):
#             return results
#         else:
#             return None
#     else:
#         done_event.wait(timeout=timeout)
#         if results:
#             return results[0]
#         else:
#             return None
#
#
# # ======================================================================================================================
# class EventListener:
#     def __init__(self, event: Condition, callback, flags=None, timeout=None, once=False,
#                  finished_callback=None):
#         """
#         Initializes the EventListener.
#
#         :param event: The event to listen for (must be a ConditionEvent or similar with filtering support).
#         :param callback: The callback function to execute when the event is triggered.
#                          The callback will receive the shared resource as an argument.
#         :param flags: Optional dictionary of filter conditions to apply (e.g. {'param1': ['a','b','c']}).
#         :param timeout: Optional timeout to wait for each event occurrence.
#         :param once: If True, the listener will stop after one execution.
#         :param finished_callback: Optional callback to execute after the main callback is done.
#         """
#         assert isinstance(event, (Condition, ConditionEvent))
#         self.event = event
#         self.flags = flags
#         self.timeout = timeout
#         self.callback = callback
#         self.once = once
#         self.finished_callback = finished_callback
#         self.kill_event = threading.Event()
#         self._running = True
#         self.thread = threading.Thread(target=self._listen)
#         self.thread.daemon = True
#
#     def _listen(self):
#         while self._running:
#
#             if isinstance(self.event, ConditionEvent):
#                 if self.flags is not None:
#                     result = self.event.wait(timeout=self.timeout, flags=self.flags)
#                 else:
#                     result = self.event.wait(timeout=self.timeout)
#             else:
#                 result = self.event.wait(timeout=self.timeout)
#             if result is not None and not self.kill_event.is_set():
#                 self._execute_callback(result)
#             if self.once:
#                 break
#
#     def _execute_callback(self, result):
#         try:
#             self.callback(result)
#         finally:
#             if self.finished_callback:
#                 self.finished_callback()
#
#     def start(self):
#         self.thread.start()
#
#     def stop(self):
#         self._running = False
#         self.kill_event.set()
#         self.thread.join()
#
#
# # ======================================================================================================================
# def event_definition(cls):
#     """
#     Decorator to make ConditionEvent fields independent for each instance.
#     If a ConditionEvent is provided as a class attribute with custom parameters,
#     a new instance with the same configuration is created for each instance.
#     """
#     original_init = cls.__init__
#
#     def new_init(self, *args, **kwargs):
#         if original_init:
#             original_init(self, *args, **kwargs)
#         for attr_name, attr_type in cls.__annotations__.items():
#             default_event = getattr(cls, attr_name, None)
#             if isinstance(default_event, ConditionEvent):
#                 new_event = ConditionEvent(flags=default_event._parameters_def, id=attr_name)
#                 setattr(self, attr_name, new_event)
#             elif attr_type is ConditionEvent:
#                 setattr(self, attr_name, ConditionEvent(id=attr_name))
#
#     cls.__init__ = new_init
#     return cls
#
#
# # ======================================================================================================================
# # Example usage of ConditionEvent with multiple condition filtering and EventListener with filter support
#
# if __name__ == '__main__':
#     @event_definition
#     class BILBO_Serial_Communication_Events:
#         # Define an event that expects two parameters: 'param1' (a str) and 'param2' (a type)
#         event_a: ConditionEvent = ConditionEvent(flags=[('param1', str), ('param2', type)])
#
#     events = BILBO_Serial_Communication_Events()
#
#     def trigger_events():
#         time.sleep(2)
#         # Trigger an event with param1 set to 'a'
#         events.event_a.set(resource="Event with param1 'a'", flags={'param1': 'a', 'param2': int})
#         time.sleep(1)
#         # Trigger an event with param1 set to 'b'
#         events.event_a.set(resource="Event with param1 'b'", flags={'param1': 'b', 'param2': int})
#         time.sleep(1)
#         # Trigger an event with param1 set to 'c'
#         events.event_a.set(resource="Event with param1 'c'", flags={'param1': 'c', 'param2': int})
#
#     # Start a thread to trigger events
#     threading.Thread(target=trigger_events).start()
#
#     # Example: waiting directly on the event with a membership condition.
#     print("Waiting for event with param1 in ['a', 'b'] (timeout 5 seconds)...")
#     result = events.event_a.wait(timeout=5, param1=['b'])
#     if result is not None:
#         print("Received:", events.event_a.get_data())
#     else:
#         print("Timeout waiting for event with param1 in ['a', 'b']")
#
#     # Example: using waitForEvents.
#     # Here we wait for event_a to have param1 equal to 'c'.
#     print("Waiting for event_a with param1 == 'c' using waitForEvents (timeout 10 seconds)...")
#     result_event = waitForEvents(events=[(events.event_a, {'param1': 'c'})], timeout=10)
#     if result_event is not None:
#         print("waitForEvents received event with id:", result_event.id, "and resource:", result_event.get_data())
#     else:
#         print("waitForEvents timed out.")

import threading
import time
from threading import Lock, Condition
import weakref
import collections


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
        with self.lock:
            self.resource = value

    def get(self):
        return self.resource

    def __enter__(self):
        self.lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()


class ConditionEvent(threading.Condition):
    id: str
    resource: 'SharedResource'
    flag: any
    _parameters_def: list

    def __init__(self, flags=None, history_size=10, id=None):
        """
        :param flags: Optional list of tuples, e.g. [('param1', str), ('param2', type)]
                      which defines the allowed parameters for the event.
        :param history_size: The maximum number of historical events to store.
        :param id: Optional identifier for the event. If not provided explicitly, the event_handler
                   decorator will set the id to the attribute name.
        """
        super().__init__()
        self.id = id
        self.resource = SharedResource()
        self.flag = None
        self._parameters_def = flags if flags is not None else []
        self._last_set_time = None
        # List of listeners. Each listener is a tuple: (callback_ref, flags, once, input_resource)
        self._listeners = []
        # Deque to store history events as tuples: (timestamp, flags)
        self._event_history = collections.deque(maxlen=history_size)

    def on(self, callback, flags=None, once=False, input_resource=True):
        """
        Register a callback to be called once the event is set and the flags match.
        The callback will be executed in a separate oneshot thread.
        If input_resource is True, the callback will be called with the event's resource data;
        otherwise, it will be called without any arguments.
        """
        try:
            if hasattr(callback, '__self__') and callback.__self__ is not None:
                callback_ref = weakref.WeakMethod(callback)
            else:
                callback_ref = callback
        except Exception:
            callback_ref = callback

        with self:
            self._listeners.append((callback_ref, flags, once, input_resource))

    def set(self, resource=None, flags=None):
        """
        Notify all waiting threads and optionally update the shared resource.
        Also triggers any registered listener callbacks if their filtering flags match.
        """
        with self:
            if self._parameters_def:
                # Validate provided flags if parameters are defined.
                if flags is not None:
                    if not isinstance(flags, dict):
                        raise ValueError("Flag must be provided as a dictionary if provided with parameters: {}".format(
                            self._parameters_def))
                    allowed_keys = {p[0] for p in self._parameters_def}
                    for key, value in flags.items():
                        if key not in allowed_keys:
                            raise ValueError("Unexpected parameter: {}".format(key))
                        for param_name, param_type in self._parameters_def:
                            if key == param_name:
                                # Allow the flag value to be a list or tuple of allowed types.
                                if isinstance(value, (list, tuple)):
                                    if not all(isinstance(v, param_type) for v in value):
                                        raise TypeError(
                                            "Each item for parameter '{}' must be of type {}".format(key, param_type))
                                elif not isinstance(value, param_type):
                                    raise TypeError("Parameter '{}' must be of type {}".format(key, param_type))
            self.flag = flags
            self.resource.set(resource)
            timestamp = time.time()
            self._last_set_time = timestamp
            self._event_history.append((timestamp, self.flag))
            self.notify_all()

            # Process listeners.
            to_call = []
            remaining_listeners = []
            for callback_ref, listener_flags, once_flag, input_resource in self._listeners:
                if self._check_flag(listener_flags):
                    to_call.append((callback_ref, input_resource))
                    if not once_flag:
                        remaining_listeners.append((callback_ref, listener_flags, once_flag, input_resource))
                else:
                    remaining_listeners.append((callback_ref, listener_flags, once_flag, input_resource))
            self._listeners = remaining_listeners

        for callback_ref, input_resource in to_call:
            # Always resolve weak references to get the actual callback.
            if isinstance(callback_ref, weakref.WeakMethod):
                callback_func = callback_ref()
            else:
                callback_func = callback_ref
            if callback_func is None:
                continue
            threading.Thread(target=self._call_listener, args=(callback_func, input_resource)).start()

    def _call_listener(self, callback, input_resource):
        try:
            if input_resource:
                data = self.get_data()
                callback(data)
            else:
                callback()
        except Exception as e:
            print("Error in listener callback:", e)

    def _check_flag(self, filter_params):
        if not filter_params:
            return True
        if not isinstance(self.flag, dict):
            return False
        for key, condition in filter_params.items():
            if key not in self.flag:
                return False
            actual = self.flag[key]

            # Handle if the actual flag is a list/tuple/set.
            if isinstance(actual, (list, tuple, set)):
                # If listener condition is also a collection, check for any intersection.
                if isinstance(condition, (list, tuple, set)):
                    if not set(actual).intersection(condition):
                        return False
                else:
                    if condition not in actual:
                        return False
            else:
                # actual is not a collection
                if isinstance(condition, (list, tuple, set)):
                    if actual not in condition:
                        return False
                elif callable(condition):
                    if not condition(actual):
                        return False
                else:
                    if actual != condition:
                        return False
        return True

    def _match_flags(self, event_flags, conditions):
        """
        Check if the provided event_flags match the filtering conditions.
        """
        if not conditions:
            return True
        if not isinstance(event_flags, dict):
            return False
        for key, condition in conditions.items():
            if key not in event_flags:
                return False
            actual = event_flags[key]
            if isinstance(condition, (list, tuple, set)):
                if actual not in condition:
                    return False
            elif callable(condition):
                if not condition(actual):
                    return False
            else:
                if actual != condition:
                    return False
        return True

    def wait(self, timeout=None, stale_event_time=None, flags: dict = None, resource_filter=None, **filter_params):
        """
        Wait for the condition to be notified and for the flags to match the given criteria.
        Additionally, if stale_event_time is provided, check if an event was set within that time.
        Additionally, if resource_filter is provided, check if the event's resource satisfies the given condition.
        For example, if the resource is a dict, you can wait until a given key has a specific value.
        If the resource is not shaped as assumed by resource_filter, the check safely fails.

        :param timeout: Optional timeout for the wait.
        :param stale_event_time: Optional duration (in seconds) within which a recent event (with matching flags)
                                 will immediately satisfy the wait.
        :param flags: Optional dict of flags to filter event parameters.
        :param resource_filter: Optional filter to apply to the resource. If a dict, each key-value pair is compared
                                against the resource (if it is a dict). Otherwise, a simple equality check is performed.
        :param filter_params: Additional key-value pairs to filter event parameters.
        :return: True if the condition was met, False if the wait timed out.
        """

        def _check_resource(data, resource_filter):
            try:
                if isinstance(resource_filter, dict) and isinstance(data, dict):
                    for key, value in resource_filter.items():
                        if data.get(key) != value:
                            return False
                    return True
                else:
                    return data == resource_filter
            except Exception:
                return False

        with self:
            # Merge filtering conditions.
            conditions = {}
            if flags:
                conditions.update(flags)
            if filter_params:
                conditions.update(filter_params)

            # Check event history for a recent event that matches the conditions.
            if stale_event_time is not None:
                now = time.time()
                for ts, event_flags in self._event_history:
                    if now - ts <= stale_event_time and self._match_flags(event_flags, conditions):
                        if resource_filter is not None:
                            data = self.get_data()
                            if _check_resource(data, resource_filter):
                                return True
                        else:
                            return True

            end_time = time.time() + timeout if timeout is not None else None

            while True:
                remaining = end_time - time.time() if end_time is not None else None
                if remaining is not None and remaining <= 0:
                    return False
                super().wait(remaining)
                if self._check_flag(conditions):
                    if resource_filter is not None:
                        data = self.get_data()
                        if _check_resource(data, resource_filter):
                            return True
                    else:
                        return True

    def get_data(self):
        with self.resource:
            return self.resource.get()

    def clear_data(self):
        with self:
            self.resource.acquire()
            self.resource.set(None)
            self.resource.release()

    def reset(self):
        with self:
            self.flag = None
            self._last_set_time = None
            self.resource.set(None)


def waitForEvents(events: list, timeout=None, wait_for_all=False):
    """
    Wait for one or more events with corresponding flag conditions.

    :param events: A list of tuples (event, flags), where 'flags' is a dictionary used to filter event parameters.
                   Example: [(event1, {'value1': 2}), (event2, {'value33': 'hello'}), (event3, None)]
    :param timeout: Overall timeout in seconds.
    :param wait_for_all: If False, returns as soon as one event is triggered with matching flags;
                         if True, waits until all events are triggered with matching flags.
    :return: If wait_for_all is False, returns the first event that meets its flags.
             If wait_for_all is True, returns a list of events in the same order as provided.
             Returns None if the timeout expires.
    """
    results = []
    lock = threading.Lock()
    done_event = threading.Event()
    threads = []
    start_time = time.time()

    for i, value in enumerate(events):
        if isinstance(value, ConditionEvent):
            events[i] = (value, None)

    def worker(ev, flags, overall_timeout):
        remaining = overall_timeout - (time.time() - start_time) if overall_timeout is not None else None
        if remaining is not None and remaining <= 0:
            return
        ret = ev.wait(timeout=remaining, flags=flags)
        if ret:
            with lock:
                results.append(ev)
            if not wait_for_all:
                done_event.set()

    # Start a thread for each event.
    for ev, flags in events:
        t = threading.Thread(target=worker, args=(ev, flags, timeout))
        t.daemon = True
        t.start()
        threads.append(t)

    if wait_for_all:
        # Wait for all threads to finish, taking into account the overall timeout.
        for t in threads:
            remaining = timeout - (time.time() - start_time) if timeout is not None else None
            t.join(timeout=remaining)
        if len(results) == len(events):
            return results
        else:
            return None
    else:
        done_event.wait(timeout=timeout)
        if results:
            return results[0]
        else:
            return None


# ======================================================================================================================
class EventListener:
    def __init__(self, event: Condition, callback, flags=None, timeout=None, once=False,
                 finished_callback=None):
        """
        Initializes the EventListener.

        :param event: The event to listen for (must be a ConditionEvent or similar with filtering support).
        :param callback: The callback function to execute when the event is triggered.
                         The callback will receive the shared resource as an argument.
        :param flags: Optional dictionary of filter conditions to apply (e.g. {'param1': ['a','b','c']}).
        :param timeout: Optional timeout to wait for each event occurrence.
        :param once: If True, the listener will stop after one execution.
        :param finished_callback: Optional callback to execute after the main callback is done.
        """
        assert isinstance(event, (Condition, ConditionEvent))
        self.event = event
        self.flags = flags
        self.timeout = timeout
        self.callback = callback
        self.once = once
        self.finished_callback = finished_callback
        self.kill_event = threading.Event()
        self._running = True
        self.thread = threading.Thread(target=self._listen)
        self.thread.daemon = True

    def _listen(self):
        while self._running:

            if isinstance(self.event, ConditionEvent):
                if self.flags is not None:
                    result = self.event.wait(timeout=self.timeout, flags=self.flags)
                else:
                    result = self.event.wait(timeout=self.timeout)
            else:
                result = self.event.wait(timeout=self.timeout)
            if result is not None and not self.kill_event.is_set():
                self._execute_callback(result)
            if self.once:
                break

    def _execute_callback(self, result):
        try:
            self.callback(result)
        finally:
            if self.finished_callback:
                self.finished_callback()

    def start(self):
        self.thread.start()

    def stop(self):
        self._running = False
        self.kill_event.set()
        if hasattr(self, 'thread') and self.thread is not None and self.thread.is_alive():
            self.thread.join()


# ======================================================================================================================
def event_definition(cls):
    """
    Decorator to make ConditionEvent fields independent for each instance.
    If a ConditionEvent is provided as a class attribute with custom parameters,
    a new instance with the same configuration is created for each instance.
    """
    original_init = cls.__init__

    def new_init(self, *args, **kwargs):
        if original_init:
            original_init(self, *args, **kwargs)
        for attr_name, attr_type in cls.__annotations__.items():
            default_event = getattr(cls, attr_name, None)
            if isinstance(default_event, ConditionEvent):
                new_event = ConditionEvent(flags=default_event._parameters_def, id=attr_name)
                setattr(self, attr_name, new_event)
            elif attr_type is ConditionEvent:
                setattr(self, attr_name, ConditionEvent(id=attr_name))

    cls.__init__ = new_init
    return cls


# ======================================================================================================================
# Example usage of ConditionEvent with multiple condition filtering and EventListener with filter support
# ==============================================================================================================
# Additional test for .on() functionality.
def test_on_functionality():
    print("\n--- Starting test of .on() functionality ---")
    # Dictionary to collect test results.
    results = {
        "with_input": [],
        "without_input": [],
        "once": 0,
        "filtered": 0,
    }

    # Create a separate event with a flag definition.
    event_test = ConditionEvent(flags=[("test_flag", str)])

    def cb_with_input(resource):
        print("cb_with_input received resource:", resource)
        results["with_input"].append(resource)

    def cb_without_input():
        print("cb_without_input called.")
        results["without_input"].append("called")

    def cb_once(resource):
        print("cb_once received resource:", resource)
        results["once"] += 1

    def cb_filtered(resource):
        print("cb_filtered received resource:", resource)
        results["filtered"] += 1

    # Register listeners for different functionalities.
    # Will always trigger (no flag filtering) and receive the resource.
    event_test.on(cb_with_input, input_resource=True)
    # Will always trigger and should not receive any resource.
    event_test.on(cb_without_input, input_resource=False)
    # Trigger only once.
    event_test.on(cb_once, once=True, input_resource=True)
    # Only trigger when flag "test_flag" equals "pass".
    event_test.on(cb_filtered, flags={"test_flag": "pass"}, input_resource=True)

    # Trigger an event that does not match the filtering flag for cb_filtered.
    print("Triggering event with test_flag: 'fail'")
    event_test.set(resource="Resource 1", flags={"test_flag": "fail"})
    time.sleep(0.5)
    # Trigger an event that will match the filtering flag.
    print("Triggering event with test_flag: 'pass'")
    event_test.set(resource="Resource 2", flags={"test_flag": "pass"})
    time.sleep(0.5)
    # Trigger another event matching the filtering flag.
    print("Triggering event with test_flag: 'pass' again")
    event_test.set(resource="Resource 3", flags={"test_flag": "pass"})
    time.sleep(0.5)

    print("\nTest on() functionality results:")
    print(results)
    print("--- Finished test of .on() functionality ---\n")



if __name__ == '__main__':
    test_on_functionality()
    # @event_definition
    # class BILBO_Serial_Communication_Events:
    #     # Define an event that expects two parameters: 'param1' (a str) and 'param2' (a type)
    #     event_a: ConditionEvent = ConditionEvent(flags=[('param1', str), ('param2', type)])
    #
    # events = BILBO_Serial_Communication_Events()
    #
    # def trigger_events():
    #     time.sleep(2)
    #     # Trigger an event with param1 set to 'a'
    #     events.event_a.set(resource="Event with param1 'a'", flags={'param1': 'a', 'param2': int})
    #     time.sleep(1)
    #     # Trigger an event with param1 set to 'b'
    #     events.event_a.set(resource="Event with param1 'b'", flags={'param1': 'b', 'param2': int})
    #     time.sleep(1)
    #     # Trigger an event with param1 set to 'c'
    #     events.event_a.set(resource="Event with param1 'c'", flags={'param1': 'c', 'param2': int})
    #
    # # Start a thread to trigger events
    # threading.Thread(target=trigger_events).start()
    #
    # # Example: waiting directly on the event with a membership condition.
    # print("Waiting for event with param1 in ['a', 'b'] (timeout 5 seconds)...")
    # result = events.event_a.wait(timeout=5, param1=['b'])
    # if result is not None:
    #     print("Received:", events.event_a.get_data())
    # else:
    #     print("Timeout waiting for event with param1 in ['a', 'b']")
    #
    # # Example: using waitForEvents.
    # # Here we wait for event_a to have param1 equal to 'c'.
    # print("Waiting for event_a with param1 == 'c' using waitForEvents (timeout 10 seconds)...")
    # result_event = waitForEvents(events=[(events.event_a, {'param1': 'c'})], timeout=10)
    # if result_event is not None:
    #     print("waitForEvents received event with id:", result_event.id, "and resource:", result_event.get_data())
    # else:
    #     print("waitForEvents timed out.")
