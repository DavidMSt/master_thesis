import math
import time

from core.utils.exit import register_exit_callback
from core.utils.plotting import RealTimePlot
from robots.bilbo.robot.bilbo_core import BILBO_Core
from robots.bilbo.robot.bilbo_data import BILBO_STATE_DATA_DEFINITIONS


# ======================================================================================================================
class BILBO_Utilities:
    live_plots: list[dict]

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, core: BILBO_Core):
        self.core = core
        self.live_plots = []
        register_exit_callback(self.close)

    # ------------------------------------------------------------------------------------------------------------------
    def close(self):
        self.closeLivePlots()

    # ------------------------------------------------------------------------------------------------------------------
    def test(self, input, timeout=1):
        try:
            data = self.core.device.function(function='test',
                                             data={'input': input},
                                             return_type=dict,
                                             request_response=True,
                                             timeout=timeout)
        except TimeoutError:
            data = None
        return data

    # ------------------------------------------------------------------------------------------------------------------
    def openLivePlot(self, state_name: str):
        if state_name not in BILBO_STATE_DATA_DEFINITIONS:
            self.core.logger.error(f"State '{state_name}' not a valid state name.")
            return

        # Check if we already have a live plot with this state
        for live_plot in self.live_plots:
            if live_plot["state_name"] == state_name:
                self.core.logger.warning(f"Live plot for state '{state_name}' already exists.")
                return

        if BILBO_STATE_DATA_DEFINITIONS[state_name]['unit'] == 'rad':
            min_val = math.degrees(BILBO_STATE_DATA_DEFINITIONS[state_name]['min'])
        else:
            min_val = BILBO_STATE_DATA_DEFINITIONS[state_name]['min']

        if BILBO_STATE_DATA_DEFINITIONS[state_name]['unit'] == 'rad':
            max_val = math.degrees(BILBO_STATE_DATA_DEFINITIONS[state_name]['max'])
        else:
            max_val = BILBO_STATE_DATA_DEFINITIONS[state_name]['max']

        plot = RealTimePlot(window_length=10,
                            signals_info=[
                                {"name": state_name, "ymin": min_val,
                                 "ymax": max_val}],
                            title=f"{self.core.id}: {state_name}",
                            value_format=BILBO_STATE_DATA_DEFINITIONS[state_name]['display_resolution'])

        plot.start()

        plot.callbacks.close.register(self._livePlotClosed_callback, inputs={"plot": plot})

        self.live_plots.append({
            "state_name": state_name,
            "plot": plot
        })

    # ------------------------------------------------------------------------------------------------------------------
    def closeLivePlots(self, state_name: str = None):

        if state_name is None:

            # Close all live plots
            live_plots = self.live_plots.copy()
            for live_plot in live_plots:
                live_plot["plot"].close()
                self.live_plots.remove(live_plot)
                self.core.logger.info(f"Closed live plot: {live_plot['state_name']}")

        else:
            for live_plot in self.live_plots:
                if live_plot["state_name"] == state_name:
                    live_plot["plot"].close()
                    self.live_plots.remove(live_plot)
                    self.core.logger.info(f"Closed live plot: {live_plot['state_name']}")
                    break

    # ------------------------------------------------------------------------------------------------------------------
    def test_response_time(self, iterations=10, print_response_time=False):
        """
        Measures the response time of the Frodo robot's test method over multiple iterations.

        Args:
            iterations (int, optional): Number of test iterations. Defaults to 10.
            print_response_time (bool, optional): Whether to print individual response times. Defaults to False.

        Logs:
            - Total number of timeouts.
            - Maximum, minimum, and average response times in milliseconds.
        """
        response_times: list[(None, float)] = [None] * iterations  # type: ignore
        timeouts = 0  # Counter for timeouts

        self.core.logger.info("Testing response time")

        # Perform an initial write to check if the robot responds
        data = self.test("HALLO", timeout=1)

        if data is None:
            self.core.logger.warning("Initial write timed out")
            return  # Exit the function if initial test fails

        for i in range(iterations):
            start = time.perf_counter()  # Record start time
            data = self.test("HALLO", timeout=1)  # Send test message

            if data is None:
                timeouts += 1  # Increment timeout counter
                response_times[i] = None
            else:
                response_times[i] = time.perf_counter() - start  # Calculate response time

            # Log response time or timeout occurrence
            if print_response_time and data is not None:
                self.core.logger.info(f"{i + 1}/{iterations} Response time: {(response_times[i] * 1000):.2f} ms")
            else:
                self.core.logger.warning(f"{i + 1}/{iterations} Timeout")

            time.sleep(0.25)  # Delay before next test iteration

        # Filter out None values (timeouts) from response times
        valid_times = [response_time for response_time in response_times if response_time is not None]

        # Calculate statistics
        max_time = max(valid_times)  # Maximum response time
        min_time = min(valid_times)  # Minimum response time
        avg_time = sum(valid_times) / len(valid_times)  # Average response time

        # Log results
        self.core.logger.info(f"Timeouts: {timeouts}")
        self.core.logger.info(f"Max time: {max_time * 1000:.2f} ms")
        self.core.logger.info(f"Min time: {min_time * 1000:.2f} ms")
        self.core.logger.info(f"Average time: {avg_time * 1000:.2f} ms")

    # ------------------------------------------------------------------------------------------------------------------
    def _livePlotClosed_callback(self, plot, *args, **kwargs):

        for live_plot in self.live_plots:
            if live_plot["plot"] == plot:
                self.live_plots.remove(live_plot)
                self.core.logger.info(f"Closed live plot: {live_plot['state_name']}")
                break
