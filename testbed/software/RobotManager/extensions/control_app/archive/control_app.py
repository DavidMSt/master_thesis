# import asyncio
# import json
# import math
# import threading
# import time
# import socket
# import uuid
# from abc import ABC, abstractmethod
# from pydoc import parentname
# from tkinter import Button
# from tokenize import group
#
# import aiohttp
# import requests
# from aiohttp import web, WSMessage
# from aiohttp.web_response import Response
# from zeroconf import Zeroconf, ServiceInfo
#
# # === CUSTOM PACKAGES ==================================================================================================
# from core.utils.logging_utils import Logger
# from core.utils.callbacks import callback_definition, CallbackContainer
# from core.utils.network.network import getLocalAndUsbIPs, getValidHostIP
#


# TODO:
#
# - Add Back Button
# - Add a way to adapt the path bar in the webapp
# - Figure out child and parent disconnects
# - Figure out why the child lags when it is looking for a parent
# -

def rgb_to_hex(rgb):
    """
    Convert a list of RGB values (0-1 floats) to a hex HTML color.
    Example: [0.5, 0.2, 0.8] -> "#8033cc"
    """
    return "#{:02x}{:02x}{:02x}".format(
        int(rgb[0] * 255),
        int(rgb[1] * 255),
        int(rgb[2] * 255)
    )


logger = Logger('Control App')
logger.setLevel('DEBUG')


@callback_definition
class WidgetCallbacks:
    clicked: CallbackContainer


class Widget(ABC):
    widget_id: str
    uid: str
    group: ('WidgetGroup', None)
    app: ('ControlApp', None)

    position: tuple
    size: tuple
    lockable: bool
    locked: bool
    callbacks: WidgetCallbacks

    def __init__(self, widget_id, position=None, size=None, lockable=False, locked=False):
        self.widget_id = widget_id
        self.position = position
        self.size = size if size else (1, 1)
        self.lockable = lockable
        self.locked = locked
        self.group = None
        self.app = None
        self.callbacks = WidgetCallbacks()

    @abstractmethod
    async def get_payload(self):
        ...

    @property
    def uid(self):
        uid = self.widget_id
        parent = self.group
        while parent is not None:
            uid = f"{parent.group_id}/{uid}"
            parent = parent.group
        return uid


# =============================================================================
# Button Callback Classes
# =============================================================================

@callback_definition
class ButtonCallbacks:
    clicked: CallbackContainer
    double_clicked: CallbackContainer
    long_pressed: CallbackContainer


@callback_definition
class MultiStateButtonCallbacks:
    clicked: CallbackContainer
    state_changed: CallbackContainer
    double_clicked: CallbackContainer
    long_pressed: CallbackContainer


@callback_definition
class MultiSelectButtonCallbacks:
    value_changed: CallbackContainer


# New callback definitions for SplitButton
@callback_definition
class SplitButtonCallbacks:
    part_clicked: CallbackContainer
    part_double_clicked: CallbackContainer
    part_long_pressed: CallbackContainer


# =============================================================================
# Button Classes
# =============================================================================

class Button(Widget):
    callbacks: ButtonCallbacks

    def __init__(self, widget_id, text, color: (str, list) = None, textcolor: (str, list) = None,
                 size=None, position=None, lockable=False, locked=False):

        super().__init__(widget_id, position=position, size=size, lockable=lockable, locked=locked)
        self.text = text  # Display text

        if color is None:
            color = [0.2, 0.2, 0.2]

        if textcolor is None:
            textcolor = [1, 1, 1]

        if isinstance(color, list):
            color = rgb_to_hex(color)
        if isinstance(textcolor, list):
            textcolor = rgb_to_hex(textcolor)

        self.color = color  # Button background color
        self.textcolor = textcolor
        self.toggle_state = False  # Example state (e.g. for toggles)

        self.callbacks = ButtonCallbacks()

    # ------------------------------------------------------------------------------------------------------------------
    async def on_pressed(self):
        self.toggle_state = not self.toggle_state
        self.callbacks.clicked.call()
        logger.debug(f"Button {self.uid} pressed")

    # ------------------------------------------------------------------------------------------------------------------
    async def on_double_click(self):
        self.callbacks.double_clicked.call()
        logger.debug(f"Button {self.uid} double clicked")

    # ------------------------------------------------------------------------------------------------------------------
    async def on_long_pressed(self):
        self.callbacks.long_pressed.call()
        logger.debug(f"Button {self.uid} long pressed")

    # ------------------------------------------------------------------------------------------------------------------
    async def get_payload(self):
        return {
            "id": self.uid,
            "name": self.text,
            "color": self.color,
            "textcolor": self.textcolor,
            "is_folder": False,
            "lockable": self.lockable,  # Now only indicates whether locking is supported
            "locked": self.locked  # NEW: Indicates the current locked state
        }

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_text(self, new_text):
        self.text = new_text
        if self.app:
            await self.app.update_widget({
                "type": "update_button",
                "id": self.uid,
                "text": self.text,
                "color": self.color,
                "textcolor": self.textcolor
            })

    # ------------------------------------------------------------------------------------------------------------------
    def set_text(self, new_text):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._set_text(new_text), self.app.event_loop)
        else:
            asyncio.run(self._set_text(new_text))

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_color(self, new_color):
        if isinstance(new_color, list):
            new_color = rgb_to_hex(new_color)
        self.color = new_color
        if self.app:
            await self.app.update_widget({
                "type": "update_button",
                "id": self.uid,
                "text": self.text,
                "color": self.color,
                "textcolor": self.textcolor
            })

    # ------------------------------------------------------------------------------------------------------------------
    def set_color(self, new_color):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._set_color(new_color), self.app.event_loop)
        else:
            asyncio.run(self._set_color(new_color))

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_textcolor(self, new_textcolor):
        if isinstance(new_textcolor, list):
            new_textcolor = rgb_to_hex(new_textcolor)
        self.textcolor = new_textcolor
        if self.app:
            await self.app.update_widget({
                "type": "update_button",
                "id": self.uid,
                "text": self.text,
                "color": self.color,
                "textcolor": self.textcolor
            })

    # ------------------------------------------------------------------------------------------------------------------
    def set_textcolor(self, new_textcolor):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._set_textcolor(new_textcolor), self.app.event_loop)
        else:
            asyncio.run(self._set_textcolor(new_textcolor))


# ======================================================================================================================
class SplitButton(Button):
    callbacks: SplitButtonCallbacks

    def __init__(self, widget_id, split: tuple, texts: list, colors: list = None, textcolors: list = None,
                 size=None, position=None, lockable=False, locked=False):
        super().__init__(widget_id, text="", color=None, textcolor=None, size=size, position=position,
                         lockable=lockable,
                         locked=locked)

        self.split = split  # Tuple (vertical_parts, horizontal_parts)
        total_parts = split[0] * split[1]
        if len(texts) != total_parts:
            raise ValueError(f"SplitButton expects {total_parts} texts for parts but got {len(texts)}")
        self.part_texts = texts
        if colors is None:
            self.part_colors = ["#555555"] * total_parts
        else:
            if isinstance(colors[0], (list, tuple)):
                self.part_colors = [rgb_to_hex(c) for c in colors]
            else:
                self.part_colors = colors
        if textcolors is None:
            self.part_textcolors = ["#FFFFFF"] * total_parts
        else:
            if isinstance(textcolors[0], (list, tuple)):
                self.part_textcolors = [rgb_to_hex(tc) for tc in textcolors]
            else:
                self.part_textcolors = textcolors

        self.callbacks = SplitButtonCallbacks()

    # ------------------------------------------------------------------------------------------------------------------
    async def get_payload(self):
        total_parts = self.split[0] * self.split[1]
        payload = {
            "id": self.uid,
            "widget_type": "split_button",
            "split": self.split,
            "parts": [],
            "lockable": self.lockable,  # NEW
            "locked": self.locked  # NEW
        }
        for i in range(total_parts):
            payload["parts"].append({
                "text": self.part_texts[i],
                "color": self.part_colors[i],
                "textcolor": self.part_textcolors[i]
            })
        return payload

    # ------------------------------------------------------------------------------------------------------------------
    async def on_part_pressed(self, part_index):
        self.callbacks.part_clicked.call(part_index)
        logger.debug(f"SplitButton {self.uid} part {part_index} pressed")

    # ------------------------------------------------------------------------------------------------------------------
    async def on_part_double_click(self, part_index):
        self.callbacks.part_double_clicked.call(part_index)
        logger.debug(f"SplitButton {self.uid} part {part_index} double clicked")

    # ------------------------------------------------------------------------------------------------------------------
    async def on_part_long_pressed(self, part_index):
        self.callbacks.part_long_pressed.call(part_index)
        logger.debug(f"SplitButton {self.uid} part {part_index} long pressed")


# ======================================================================================================================
class MultiStateButton(Button):
    callbacks: MultiStateButtonCallbacks

    def __init__(self, widget_id, title, states, color=None, current_state=0, textcolor="#fff",
                 size=None, position=None, lockable=False, locked=False):
        super().__init__(widget_id, title, color, textcolor, size, position, lockable=lockable, locked=locked)
        self.states = states  # Can be list of strings or tuples (state, color)
        self.current_state = current_state
        self.callbacks = MultiStateButtonCallbacks()

    # ------------------------------------------------------------------------------------------------------------------
    def get_current_state_info(self):
        current = self.states[self.current_state]
        if isinstance(current, (list, tuple)):
            state_str = current[0]
            state_color = current[1]
            if isinstance(state_color, (list, tuple)):
                r, g, b = state_color
                state_color = f"#{int(round(r * 255)):02X}{int(round(g * 255)):02X}{int(round(b * 255)):02X}"
            return state_str, state_color
        else:
            return current, None

    # ------------------------------------------------------------------------------------------------------------------
    async def get_payload(self):
        state_str, state_color = self.get_current_state_info()
        effective_color = state_color if state_color is not None else self.color
        return {
            "id": self.uid,
            "name": self.text,
            "color": effective_color,
            "textcolor": self.textcolor,
            "widget_type": "multi_state_button",
            "states": self.states,
            "text": self.text,
            "current_state": self.current_state,
            "state": state_str,
            "is_folder": False,
            "lockable": self.lockable,  # NEW
            "locked": self.locked  # NEW
        }

    # ------------------------------------------------------------------------------------------------------------------
    async def on_pressed(self):
        await self._set_current_state((self.current_state + 1) % len(self.states))
        self.callbacks.clicked.call(self.current_state)
        logger.debug(f"Multi-State button {self.uid} pressed. Current state: {self.current_state}")

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_current_state(self, new_state):
        self.current_state = new_state
        state_str, state_color = self.get_current_state_info()
        effective_color = state_color if state_color is not None else self.color
        if self.app:
            await self.app.update_widget({
                "type": "update_multi_state",
                "id": self.uid,
                "current_state": self.current_state,
                "states": self.states,
                "text": self.text,
                "state": state_str,
                "color": effective_color,
                "textcolor": self.textcolor,
            })

        self.callbacks.state_changed.call(self.current_state)

    # ------------------------------------------------------------------------------------------------------------------
    def set_current_state(self, new_state):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._set_current_state(new_state), self.app.event_loop)
        else:
            asyncio.run(self._set_current_state(new_state))

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_states(self, new_states):
        self.states = new_states
        state_str, state_color = self.get_current_state_info()
        effective_color = state_color if state_color is not None else self.color
        if self.app:
            await self.app.update_widget({
                "type": "update_multi_state",
                "id": self.uid,
                "current_state": self.current_state,
                "states": self.states,
                "title": self.text,
                "state": state_str,
                "color": effective_color,
                "textcolor": self.textcolor
            })

    # ------------------------------------------------------------------------------------------------------------------
    def set_states(self, new_states):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._set_states(new_states), self.app.event_loop)
        else:
            asyncio.run(self._set_states(new_states))


# ======================================================================================================================
class MultiSelectButton(Button):
    callbacks: MultiSelectButtonCallbacks

    def __init__(self, widget_id, name, options, value, color=None, title="", textcolor="#fff",
                 size=None, position=None, lockable=False, locked=False):
        super().__init__(widget_id, name, color, textcolor, size, position, lockable=lockable, locked=locked)
        self.options = options  # List of dicts with keys "value" and "label"
        self.value = value
        self.title = title  # Optional title displayed above the selected option
        self.callbacks = MultiSelectButtonCallbacks()

    # ------------------------------------------------------------------------------------------------------------------
    async def get_payload(self):
        payload = {
            "id": self.uid,
            "name": self.text,
            "color": self.color,
            "textcolor": self.textcolor,
            "widget_type": "multi_select",
            "options": self.options,
            "value": self.value,
            "is_folder": False,
            "lockable": self.lockable,  # NEW
            "locked": self.locked  # NEW
        }
        if self.title:
            payload["title"] = self.title
        return payload

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_value(self, new_value):
        self.value = new_value
        if self.app:
            await self.app.update_widget({
                "type": "update_multi_select",
                "id": self.uid,
                "value": self.value
            })
        self.callbacks.value_changed.call(new_value)
        logger.debug(f"Multi-Select button {self.uid} value changed to {self.value}")

    # ------------------------------------------------------------------------------------------------------------------
    def set_value(self, new_value):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._set_value(new_value), self.app.event_loop)
        else:
            asyncio.run(self._set_value(new_value))

    # ------------------------------------------------------------------------------------------------------------------
    async def on_value_change(self, new_value):
        self.set_value(new_value)


# =============================================================================
# New Widget Classes: SliderWidget, TextWidget, DigitalNumberWidget, and JoystickWidget
# =============================================================================


class StatusWidget(Button):
    """
    A widget to display multiple status rows:
      - A colored marker (circle)
      - A name
      - A status text

    The 'items' is a list of dicts, each having keys:
       {
         "marker_color": "#FF0000",  # The circle color
         "name": "MySubsystem",
         "status": "OK"
       }
    """

    def __init__(self, widget_id, items=None, color=None, textcolor=None,
                 size=None, position=None, lockable=False, locked=False):
        super().__init__(widget_id, text="", color=color, textcolor=textcolor,
                         size=size, position=position,
                         lockable=lockable, locked=locked)
        self.items = items if items else []

    async def get_payload(self):
        base_payload = await super().get_payload()
        # We override widget_type

        base_payload["widget_type"] = "status"
        base_payload["items"] = self.items
        return base_payload

    async def _set_items(self, new_items):
        self.items = new_items
        if self.app:
            await self.app.update_widget({
                "type": "update_statuswidget",
                "id": self.uid,
                "items": self.items
            })

    def set_items(self, new_items):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._set_items(new_items), self.app.event_loop)
        else:
            asyncio.run(self._set_items(new_items))

    # --------------------------------------------------------------------------
    # NEW METHOD: Update just marker_color/status for a specific name
    # --------------------------------------------------------------------------
    async def _update_value(self, status_name, marker_color=None, status=None):
        """
        Internal async method to update the marker_color or status text
        for the row with 'name' == status_name.
        """
        # Find the corresponding item by name
        found_item = None
        for item in self.items:
            if item.get("name") == status_name:
                if marker_color is not None:
                    item["marker_color"] = marker_color
                if status is not None:
                    item["status"] = status
                found_item = item
                break

        if found_item and self.app:
            # Broadcast the full items list again to trigger a visual update
            await self.app.update_widget({
                "type": "update_statuswidget",
                "id": self.uid,
                "items": self.items
            })

    def update_value(self, status_name, marker_color=None, status=None):
        """
        Public method to update a single status row by name. You can update:
          * the marker_color only
          * the status text only
          * or both
        Example:
           my_widget.update_value("Sensor", marker_color="#00FF00", status="OK")
        """
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(
                self._update_value(status_name, marker_color, status),
                self.app.event_loop
            )
        else:
            asyncio.run(
                self._update_value(status_name, marker_color, status)
            )


@callback_definition
class SliderWidgetCallbacks:
    value_changed: CallbackContainer


class SliderWidget(Widget):
    callbacks: SliderWidgetCallbacks

    def __init__(self, widget_id, title, min_value, max_value, current_value, color="#101010", textcolor="#fff",
                 size=None, position=None, direction="horizontal", automatic_reset=None, lockable=False, locked=False):

        super(SliderWidget, self).__init__(widget_id, position=position, size=size, lockable=lockable, locked=locked)

        self.title = title
        self.min = min_value
        self.max = max_value
        self.value = current_value
        self.direction = direction  # "horizontal" (default) or "vertical"
        self.automatic_reset = automatic_reset  # Value to reset to when dragging is released
        if isinstance(color, list):
            color = rgb_to_hex(color)
        if isinstance(textcolor, list):
            textcolor = rgb_to_hex(textcolor)
        self.color = color
        self.textcolor = textcolor

        self.callbacks = SliderWidgetCallbacks()

    # ------------------------------------------------------------------------------------------------------------------
    async def get_payload(self):
        return {
            "id": self.uid,
            "widget_type": "slider",
            "title": self.title,
            "min": self.min,
            "max": self.max,
            "value": self.value,
            "color": self.color,
            "textcolor": self.textcolor,
            "direction": self.direction,
            "automatic_reset": self.automatic_reset,
            "is_folder": False,
            "lockable": self.lockable,  # NEW
            "locked": self.locked  # NEW
        }

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_value(self, new_value):
        self.value = new_value
        if self.app:
            await self.app.update_widget({
                "type": "update_slider",
                "id": self.uid,
                "value": self.value
            })

        logger.debug(f"Slider button {self.uid} value changed to {self.value}")

    # ------------------------------------------------------------------------------------------------------------------
    def set_value(self, new_value):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._set_value(new_value), self.app.event_loop)
        else:
            asyncio.run(self._set_value(new_value))

        self.callbacks.value_changed.call(new_value)

    # ------------------------------------------------------------------------------------------------------------------
    async def on_value_changed(self, new_value):
        await self._set_value(new_value)


# -----------------------------------------------
# New Joystick Widget
# -----------------------------------------------

@callback_definition
class JoystickWidgetCallbacks:
    value_changed: CallbackContainer


class JoystickWidget(Widget):
    callbacks: JoystickWidgetCallbacks

    def __init__(self, widget_id, title, initial_x=0, initial_y=0, size=None, position=None,
                 fixed_axis=None, lockable=False, locked=False):

        super(JoystickWidget, self).__init__(widget_id, position=position, size=size, lockable=lockable, locked=locked)

        self.title = title
        self.x = initial_x
        self.y = initial_y

        self.callbacks = JoystickWidgetCallbacks()

        # New: support fixing one axis. Valid values: "horizontal" or "vertical"
        self.fixed_axis = fixed_axis
        if fixed_axis == "horizontal":
            self.fixed_y = initial_y
        elif fixed_axis == "vertical":
            self.fixed_x = initial_x

    async def get_payload(self):
        payload = {
            "id": self.uid,
            "widget_type": "joystick",
            "title": self.title,
            "x": self.x,
            "y": self.y,
            "is_folder": False,
            "lockable": self.lockable,  # NEW
            "locked": self.locked  # NEW
        }
        if self.size:
            payload["grid_size"] = [self.size[0], self.size[1]]
        if self.fixed_axis is not None:
            payload["fixed_axis"] = self.fixed_axis
        return payload

    async def _set_value(self, new_x, new_y):
        # If an axis is fixed, ignore movement on that axis.
        if self.fixed_axis == "horizontal":
            new_y = self.fixed_y
        elif self.fixed_axis == "vertical":
            new_x = self.fixed_x
        self.x = new_x
        self.y = new_y
        print(f"Joystick button {self.uid} value changed to {self.x}, {self.y}")

        if self.app:
            await self.app.update_widget({
                "type": "update_joystick",
                "id": self.uid,
                "x": self.x,
                "y": self.y
            })
        self.callbacks.value_changed.call((self.x, self.y))

    def set_value(self, new_x, new_y):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._set_value(new_x, new_y), self.app.event_loop)
        else:
            asyncio.run(self._set_value(new_x, new_y))

    async def on_value_changed(self, new_x, new_y):
        await self._set_value(new_x, new_y)


# ======================================================================================================================
class TextWidget(Widget):
    def __init__(self, widget_id, title, text, color: (str, list) = None, textcolor: (str, list) = "#fff",
                 size=None, position=None, lockable=False, locked=False):

        super(TextWidget, self).__init__(widget_id, position=position, size=size, lockable=lockable, locked=locked)

        self.title = title
        self.text = text

        if color is None:
            color = [0.2, 0.2, 0.2]

        if isinstance(color, list):
            color = rgb_to_hex(color)
        if isinstance(textcolor, list):
            textcolor = rgb_to_hex(textcolor)
        self.color = color
        self.textcolor = textcolor

    # ------------------------------------------------------------------------------------------------------------------
    async def get_payload(self):
        return {
            "id": self.uid,
            "widget_type": "text",
            "title": self.title,
            "text": self.text,
            "color": self.color,
            "textcolor": self.textcolor,
            "is_folder": False,
            "lockable": self.lockable,  # NEW
            "locked": self.locked  # NEW
        }

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_text(self, new_text):
        self.text = new_text
        if self.app:
            await self.app.update_widget({
                "type": "update_text",
                "id": self.uid,
                "text": self.text
            })

    # ------------------------------------------------------------------------------------------------------------------
    def set_text(self, new_text):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._set_text(new_text), self.app.event_loop)
        else:
            asyncio.run(self._set_text(new_text))


# ======================================================================================================================
class DigitalNumberWidget(Widget):
    def __init__(self, widget_id, title, value, decimals, color, textcolor="#fff", max_digits=8,
                 size=None, position=None, lockable=False, locked=False):

        super(DigitalNumberWidget, self).__init__(widget_id, position=position, size=size, lockable=lockable,
                                                  locked=locked)

        self.title = title
        self.value = value
        self.decimals = decimals
        if isinstance(color, list):
            color = rgb_to_hex(color)
        if isinstance(textcolor, list):
            textcolor = rgb_to_hex(textcolor)
        self.color = color
        self.textcolor = textcolor
        self.max_length = max_digits + 1

    # ------------------------------------------------------------------------------------------------------------------
    async def get_payload(self):
        formatted_value = format(self.value, f".{self.decimals}f")
        return {
            "id": self.uid,
            "widget_type": "digitalnumber",
            "title": self.title,
            "value": formatted_value,
            "decimals": self.decimals,
            "color": self.color,
            "textcolor": self.textcolor,
            "is_folder": False,
            "max_length": self.max_length,
            "lockable": self.lockable,  # NEW
            "locked": self.locked  # NEW
        }

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_value(self, new_value):
        self.value = new_value
        formatted_value = format(self.value, f".{self.decimals}f")
        if self.app:
            await self.app.update_widget({
                "type": "update_digitalnumber",
                "id": self.uid,
                "value": formatted_value
            })

    # ------------------------------------------------------------------------------------------------------------------
    def set_value(self, new_value):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._set_value(new_value), self.app.event_loop)
        else:
            asyncio.run(self._set_value(new_value))


class GraphWidget(Widget):
    def __init__(self, widget_id, title, y_min, y_max, window_time, color, textcolor="#fff",
                 line_color="#00FF00", size=None, position=None, lockable=False, locked=False,
                 y_ticks=None, x_ticks_spacing=None):

        super(GraphWidget, self).__init__(widget_id, position=position, size=size, lockable=lockable, locked=locked)

        self.title = title
        self.y_min = y_min
        self.y_max = y_max
        self.window_time = window_time  # Duration (in seconds) for the rolling window
        if isinstance(color, list):
            color = rgb_to_hex(color)
        if isinstance(textcolor, list):
            textcolor = rgb_to_hex(textcolor)
        if isinstance(line_color, list):
            line_color = rgb_to_hex(line_color)
        self.color = color
        self.textcolor = textcolor
        self.line_color = line_color
        self.y_ticks = y_ticks  # Optional array of y-tick values
        self.x_ticks_spacing = x_ticks_spacing  # Optional x-axis grid spacing

    async def get_payload(self):
        return {
            "id": self.uid,
            "widget_type": "graph",
            "title": self.title,
            "y_min": self.y_min,
            "y_max": self.y_max,
            "window_time": self.window_time,
            "color": self.color,
            "textcolor": self.textcolor,
            "line_color": self.line_color,
            "is_folder": False,
            "lockable": self.lockable,
            "locked": self.locked,
            "grid_size": [self.size[0], self.size[1]],
            # Pass them along so the front-end can draw them
            "y_ticks": self.y_ticks if self.y_ticks else [],
            "x_ticks_spacing": self.x_ticks_spacing if self.x_ticks_spacing else 2,
        }

    def push_value(self, value):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._push_value(value), self.app.event_loop)
        else:
            asyncio.run(self._push_value(value))

    async def _push_value(self, value):
        # Send the new data point to the client.
        await self.app.update_widget({
            "type": "push_value",
            "id": self.uid,
            "value": value,
            'time': time.time(),
        })


class BackButton(Button):

    def __init__(self, id):
        name = 'Back'
        super(BackButton, self).__init__(id, name, color=[0.5, 0.5, 0.5], textcolor=[0, 0, 0], size=(1, 1),
                                         position=(0, 1))
        self.reserved = True

    async def on_pressed(self):
        await super(BackButton, self).on_pressed()


class HomeButton(Button):

    def __init__(self, widget_id):
        name = 'Home'
        super(HomeButton, self).__init__(widget_id, name, color=[0.5, 0.5, 0.5], textcolor=[0, 0, 0], size=(1, 1),
                                         position=(0, 0))
        self.reserved = True


class PlaceholderWidget(Widget):
    def __init__(self, position):
        super().__init__(widget_id=f"placeholder_{position[0]}_{position[1]}")
        # position is a tuple: (column, row)
        self.position = position
        self.size = (1, 1)
        # For our purposes, placeholders are marked with a flag.
        self.is_placeholder = True
        # Although placed in every cell, we do not treat them as reserved widgets.
        # Instead, _assign_position will prevent non‐reserved widgets from being
        # placed in column 0 so placeholders there can only be overwritten by reserved ones.
        self.reserved = False
        self.group = None

    async def get_payload(self):
        return {
            "widget_type": "placeholder",
            "position": [self.position[0], self.position[1]],
            "grid_size": [self.size[0], self.size[1]]
        }


class FolderWidget(Widget):
    callbacks: ButtonCallbacks
    target_group: 'WidgetGroup'

    def __init__(self, widget_id, name, target_group, color: (list, str) = "#55FF55", textcolor: (list, str) = "#fff",
                 size=(1, 1), position=None, lockable=False, locked=False):
        super().__init__(widget_id, position, size, lockable, locked)

        # IMPORTANT: Initialize the group attribute to avoid uid errors.
        self.name = name
        self.target_group = target_group  # The target WidgetGroup that this folder represents.
        self.color = color
        self.textcolor = textcolor

        self.callbacks = ButtonCallbacks()

    async def get_payload(self):
        return {
            "id": self.uid,  # The uid property now works correctly because self.group exists.
            "name": self.name,
            "color": self.color,
            "textcolor": self.textcolor,
            "widget_type": "folder",  # New type for folder widgets.
            "lockable": self.lockable,
            "locked": self.locked,
            'is_folder': True,
        }

    async def on_pressed(self):
        if self.app:
            # When pressed, switch into the target group.
            asyncio.create_task(self.target_group.setAsCurrentGroup())
        else:
            print("WARNING: WidgetGroup.on_pressed() called without an app.")

    async def on_long_pressed(self):
        ...

    async def on_double_click(self):
        ...


class ProxyFolderWidget(FolderWidget):
    def __init__(self, widget_id, name, target_group, color: (list, str) = "#55FF55", textcolor: (list, str) = "#fff",
                 size=(1, 1), position=None, lockable=False, locked=False):
        super(ProxyFolderWidget, self).__init__(widget_id, name, target_group, color, textcolor, size, position,
                                                lockable, locked)

        self.is_proxy = True

    # async def on_pressed(self):
    #     if self.app:
    #         # When pressed, switch into the target group.
    #         await self.app._setCurrentGroup(self.target_group)


class WidgetGroup:
    group: 'WidgetGroup'
    app: ('ControlApp', None)

    def __init__(self, group_id, widgets=None, group_type="folder", color: (str, list) = "#55FF55", pages=1):
        self.group_id = group_id.lower().replace(" ", "")
        self.name = group_id
        self.pages = pages  # New: number of pages supported (default 1)
        self.current_page = 0  # New: currently visible page
        # Widgets will include both “real” widgets (and groups) and placeholder widgets.
        self.widgets = []
        self.group_type = group_type  # "folder" or "modal"

        if isinstance(color, list):
            color = rgb_to_hex(color)

        self.color = color
        self.group = None
        self.app = None  # To be set later

        # The grid configuration: grid_size is defined as (rows, columns) for one page.
        self.size = (1, 1)
        self.grid_size = (2, 6)  # (rows per page, columns)
        self.position = None

        # Maintain a dictionary mapping each cell coordinate (col, row) to its placeholder widget.
        self._placeholders = {}

        # If initial children are provided, add them via our add methods.
        if widgets is not None:
            for child in widgets:
                if isinstance(child, WidgetGroup):
                    self.addGroup(child)
                else:
                    self.addWidget(child)

        # Pre-populate the entire grid with placeholders across all pages.
        self._init_placeholders()

        home_button = HomeButton(widget_id=f"home_{self.group_id}")
        self.addWidget(home_button)

        self.group = None
        self.groups = []

    # ---------------------------------------------------------------------------
    @property
    def group(self):
        return self._group

    # ---------------------------------------------------------------------------
    @group.setter
    def group(self, value):
        self._group = value
        if value is not None:
            back_button = BackButton(id=f"back_{self.group_id}")
            back_button.callbacks.clicked.register(self._back_button_callback)
            self.addWidget(back_button)

    # ---------------------------------------------------------------------------
    async def setAsCurrentGroup(self):
        if self.app:
            await self.app._setCurrentGroup(self)

    # ---------------------------------------------------------------------------
    def _back_button_callback(self):
        if self.app is not None:
            self.app.go_back()

    # ---------------------------------------------------------------------------
    def _init_placeholders(self):
        """
        Create a placeholder in every cell of the grid for each page and add them to both
        the children list and the placeholders dictionary.
        """
        grid_rows, grid_cols = self.grid_size
        total_rows = self.pages * grid_rows
        for r in range(total_rows):
            for c in range(grid_cols):
                placeholder = PlaceholderWidget((c, r))
                placeholder.group = self
                self.widgets.append(placeholder)
                self._placeholders[(c, r)] = placeholder

    # ---------------------------------------------------------------------------
    def _compute_occupancy(self, exclude=None):
        """
        Build the occupancy matrix for the grid based on the positions of non-placeholder widgets.
        Placeholders are considered available for overwriting.
        The optional 'exclude' widget (usually the one being added) is ignored.
        """
        grid_rows, grid_cols = self.grid_size
        total_rows = self.pages * grid_rows
        occupancy = [[False for _ in range(grid_cols)] for _ in range(total_rows)]
        for child in self.widgets:
            # Skip the one being assigned and skip placeholders.
            if child is exclude or getattr(child, "is_placeholder", False):
                continue
            if child.position is None:
                continue
            col, row = child.position
            w, h = child.width if hasattr(child, 'size') and child.width else (1, 1)
            for r in range(row, row + h):
                for c in range(col, col + w):
                    occupancy[r][c] = True
        return occupancy

    # ---------------------------------------------------------------------------
    def _assign_position(self, widget):
        """
        Determine a widget's grid position immediately when it is added.
        If a manual position was provided, validate that:
          - The widget fits in the grid.
          - It does not overlap any non-placeholder widgets.
          - Non-reserved widgets are not placed in column 0.
          - Widgets with a height > 1 do not cross a page boundary.
        Otherwise, auto-assign a free spot by scanning the grid (across pages) for a free spot.
        """
        if not hasattr(widget, 'size') or widget.width is None:
            widget.width = (1, 1)
        w, h = widget.width
        grid_rows, grid_cols = self.grid_size
        total_rows = self.pages * grid_rows

        reserved = getattr(widget, "reserved", False)
        min_allowed = 0 if reserved else 1

        if widget.position is not None:
            col, row = widget.position
            if col < min_allowed:
                raise ValueError(
                    f"Widget {widget.group_id} is not reserved but is trying to be placed in reserved column 0."
                )
            if row < 0 or row + h > total_rows or col < 0 or col + w > grid_cols:
                raise ValueError(
                    f"Widget {widget.group_id} with size {w}x{h} at position ({col}, {row}) does not fit in the grid."
                )
            # Ensure widget does not cross page boundary.
            if (row % grid_rows) + h > grid_rows:
                raise ValueError(
                    f"Widget {widget.group_id} with height {h} crosses page boundary at row {row}."
                )
            occupancy = self._compute_occupancy(exclude=widget)
            for r in range(row, row + h):
                for c in range(col, col + w):
                    if occupancy[r][c]:
                        raise ValueError(
                            f"Widget {widget.group_id} overlaps with another widget at cell ({c}, {r})."
                        )
            return  # The manual position is valid.

        occupancy = self._compute_occupancy(exclude=widget)
        placed = False
        for p in range(self.pages):
            for r in range(0, grid_rows - h + 1):
                overall_row = p * grid_rows + r
                for c in range(min_allowed, grid_cols - w + 1):
                    can_place = True
                    for rr in range(overall_row, overall_row + h):
                        for cc in range(c, c + w):
                            if occupancy[rr][cc]:
                                can_place = False
                                break
                        if not can_place:
                            break
                    if can_place:
                        widget.position = (c, overall_row)
                        placed = True
                        break
                if placed:
                    break
            if placed:
                break
        if not placed:
            raise ValueError(f"Not enough space to place widget {widget.group_id} with size {w}x{h}.")

    # ---------------------------------------------------------------------------
    def _remove_placeholders_in_area(self, widget):
        """
        Remove any placeholder occupying cells in the area covered by the widget.
        """
        col, row = widget.position
        w, h = widget.width
        cells = [(c, r) for r in range(row, row + h) for c in range(col, col + w)]
        for cell in cells:
            c, r = cell
            if cell in self._placeholders:
                if c == 0 and not getattr(widget, "reserved", False):
                    continue
                placeholder = self._placeholders.pop(cell)
                if placeholder in self.widgets:
                    self.widgets.remove(placeholder)

    # ---------------------------------------------------------------------------
    def addWidget(self, widget) -> 'Widget':
        """
        Add a widget to the ButtonGroup.
        """
        widget.group = self
        self.widgets.append(widget)
        self._assign_position(widget)
        self._remove_placeholders_in_area(widget)
        if self.app is not None:
            widget.app = self.app
        return widget

    # ---------------------------------------------------------------------------
    def addProxyGroup(self, group: 'ChildProxyGroup'):
        group.group = self

        folder_widget = ProxyFolderWidget(
            widget_id=f"{group.group_id}_folder",
            name=group.name,
            target_group=group,
            color=group.color  # Or choose a default folder color if preferred.
        )
        self.addWidget(folder_widget)
        self.groups.append(group)

        if self.app is not None:
            self.app.assign_app_to_tree(group)

            if self.app.current_group == self:
                self.app.send_current_group_non_async()

    # ---------------------------------------------------------------------------
    def addGroup(self, group: 'WidgetGroup'):
        # Set the parent for the group being added.
        group.group = self
        # Create a FolderWidget representing the group.
        folder_widget = FolderWidget(
            widget_id=f"{group.group_id}_folder",
            name=group.name,
            target_group=group,
            color=group.color  # Or choose a default folder color if preferred.
        )
        # Add the FolderWidget as a child into the parent's widget list.
        self.addWidget(folder_widget)

        self.groups.append(group)
        # Assign a position and remove conflicting placeholders, etc.
        self._assign_position(folder_widget)
        self._remove_placeholders_in_area(folder_widget)

        if self.app is not None:
            self.app.assign_app_to_tree(group)

            if self.app.current_group == self:
                self.app.send_current_group_non_async()

    # ---------------------------------------------------------------------------
    def removeWidget(self, widget_id):
        """
        Remove a widget (not a group) by its ID.
        """
        for child in list(self.widgets):
            if hasattr(child, "id") and child.group_id == widget_id and not isinstance(child, WidgetGroup):
                self.widgets.remove(child)
                return True
        return False

    # ---------------------------------------------------------------------------
    def removeGroup(self, group_id):
        """
        Remove a ButtonGroup (i.e. a folder) by its ID.
        """
        for child in list(self.widgets):
            if isinstance(child, WidgetGroup) and child.group_id == group_id:
                self.widgets.remove(child)
                return True
        return False

    # ---------------------------------------------------------------------------
    # def get_payload(self):
    #     """
    #     Build the payload for this group by gathering payloads from all children (widgets,
    #     groups, and placeholders) on the current page.
    #     """
    #     rows_per_page = self.grid_size[0]
    #     page_offset = self.current_page * rows_per_page
    #     widget_payloads = []
    #     for child in self.widgets:
    #         # Only include the child if its row falls in the current page.
    #         if child.position and not (page_offset <= child.position[1] < page_offset + rows_per_page):
    #             continue
    #         if isinstance(child, WidgetGroup):
    #             payload = {
    #                 "id": child.uid,
    #                 "name": child.name,
    #                 "color": child.color,
    #                 "textcolor": "#fff",
    #                 "is_folder": True
    #             }
    #         else:
    #             payload = child.get_payload()
    #         adjusted_position = [child.position[0], child.position[1] - page_offset] if child.position else [0, 0]
    #         payload["position"] = adjusted_position
    #         payload["grid_size"] = [child.size[0], child.size[1]]
    #         widget_payloads.append(payload)
    #
    #     return {
    #         "set_name": self.uid,
    #         "group_type": self.group_type,
    #         "grid_size": [self.grid_size[1], self.grid_size[0]],  # [columns, rows]
    #         "grid_items": widget_payloads,
    #         "path": self.get_path(),
    #         "current_page": self.current_page,
    #         "pages": self.pages,
    #     }

    # ---------------------------------------------------------------------------
    async def get_payload(self):
        rows_per_page = self.grid_size[0]
        page_offset = self.current_page * rows_per_page
        widget_payloads = []
        for child in self.widgets:
            # Only include children whose row is on the current page.
            if child.position and not (page_offset <= child.position[1] < page_offset + rows_per_page):
                continue
            # # If the child is actually a sub-group, wrap it in a FolderWidget
            # if isinstance(child, WidgetGroup):
            #     folder_widget = FolderWidget(
            #         widget_id=child.group_id,
            #         name=child.name,
            #         target_group=child,  # the group you’d like to enter on press
            #         color=child.color,
            #         # Optionally, you can pass other properties (like lockable, locked) from the child
            #     )
            #     payload = folder_widget.get_payload()
            # else:
            payload = await child.get_payload()
            adjusted_position = [child.position[0], child.position[1] - page_offset] if child.position else [0, 0]
            payload["position"] = adjusted_position
            payload["grid_size"] = [child.width[0], child.width[1]]
            widget_payloads.append(payload)

        return {
            "set_name": self.uid,
            "group_type": self.group_type,
            "grid_size": [self.grid_size[1], self.grid_size[0]],  # [columns, rows]
            "grid_items": widget_payloads,
            "path": self.get_path(),
            "current_page": self.current_page,
            "pages": self.pages,
        }

    def get_root(self):
        current = self
        while current.group is not None:
            current = current.group
        return current

    # # ---------------------------------------------------------------------------
    # def getButtonByPath(self, path):
    #     if path.startswith('/'):
    #         current = self.get_root()
    #         tokens = path.strip('/').split('/')
    #     elif path.startswith('./'):
    #         current = self
    #         tokens = path[2:].split('/')
    #     else:
    #         current = self
    #         tokens = path.split('/')
    #
    #     for token in tokens:
    #         found = None
    #         for child in current.widgets:
    #             if hasattr(child, "id") and child.group_id == token:
    #                 found = child
    #                 break
    #         if found is None:
    #             return None
    #         if token != tokens[-1]:
    #             if isinstance(found, WidgetGroup):
    #                 current = found
    #             else:
    #                 return None
    #         else:
    #             return found
    #     return current
    def getByPath(self, path: str):
        """
        Resolves a widget or group by path relative to this group.
        Accepts both absolute paths ("/root/folder/button"),
        relative paths ("./folder/button"), or simple token paths ("folder/button").
        Comparison is case- and space-insensitive.
        Returns the widget/group if found, or None.
        """
        # Choose the starting group:
        if path.startswith("/"):
            current = self.get_root()  # Assumes get_root() is defined to retrieve the top-level group.
            tokens = path.strip("/").split("/")
        elif path.startswith("./"):
            current = self
            tokens = path[2:].split("/")
        else:
            current = self
            tokens = path.split("/")

        # Helper for name normalization.
        def normalize(name: str) -> str:
            return name.lower().replace(" ", "")

        # For an absolute path, ensure the first token matches the root's id.
        if tokens and normalize(tokens[0]) != normalize(current.group_id):
            return None

        # Traverse each token in the path after the first.
        # Only groups can have children so for nonterminal tokens, enforce that constraint.
        for i, token in enumerate(tokens[1:], start=1):
            token_norm = normalize(token)
            found = None

            # Check both group children and widgets.
            # (Assuming that groups are stored in self.groups and widgets in self.widgets.)
            for child in current.groups + current.widgets:
                if isinstance(child, WidgetGroup) and normalize(child.group_id) == token_norm:
                    found = child
                    break
                elif hasattr(child, "widget_id") and normalize(child.widget_id) == token_norm:
                    found = child
                    break

            if found is None:
                return None

            # If there are still tokens left, only a group can contain further tokens.
            if i < len(tokens) - 1:
                if isinstance(found, WidgetGroup):
                    current = found
                else:
                    return None
            else:
                return found

        return current

    # ---------------------------------------------------------------------------
    def get_path(self):
        if self.group is None:
            return "/" + self.group_id
        else:
            return self.group.get_path().rstrip("/") + "/" + self.group_id

    # ---------------------------------------------------------------------------
    @property
    def uid(self):
        return self.get_path()


# ======================================================================================================================
class ChildProxyGroup(WidgetGroup):
    child_app: 'ControlAppChild'
    path: str

    def __init__(self, group_id, child_app, path_in_parent_app, widgets=None, group_type="folder",
                 color: (str, list) = "#55FF55",
                 pages=1):
        super().__init__(group_id, widgets=None, group_type="folder", color=color, pages=pages)
        self.child_app = child_app
        self.path = path_in_parent_app

    # ------------------------------------------------------------------------------------------------------------------
    async def setAsCurrentGroup(self):
        if self.app:
            await self.app._setCurrentGroup(self)
            self.app.set_active_child(self.child_app)

        # asyncio.create_task(self.parent_app.setCurrentGroup(self.path))
        await self.child_app.setCurrentGroup(self.path)

    # ------------------------------------------------------------------------------------------------------------------
    async def get_payload(self):
        payload = await self.child_app.get_folder_payload(self.path)

        if payload is not None:
            return payload
        else:
            return await super(ChildProxyGroup, self).get_payload()


# ======================================================================================================================
class ControlAppChild:
    id: str
    address: str
    port: int

    folder_path: str

    def __init__(self, app_id, address, port, root_folder, websocket, app: 'ControlApp'):
        self.id = app_id
        self.address = address
        self.port = port
        self.websocket = websocket
        self.root_folder = root_folder
        self.folder_path = ''

        self.pending_requests = {}

        self.root_group = ChildProxyGroup(group_id=self.id,
                                          path_in_parent_app=f"{self.root_folder}",
                                          child_app=self)

        self.app = app


        self.path_in_child_app = ''

    # ------------------------------------------------------------------------------------------------------------------
    async def get_folder_payload(self, folder_path):
        # Generate a unique correlation ID
        request_id = str(uuid.uuid4())

        # Create a Future to wait for the response
        future = self.app.loop.create_future()
        self.pending_requests[request_id] = future

        # Prepare the message with the folder path and the unique request ID
        message = {
            'type': 'request',
            'request_type': 'get_folder_payload',
            'folder_path': folder_path,
            'request_id': request_id
        }

        # Send the request message to the child via the WebSocket connection
        await self.websocket.send_json(message)

        try:
            # Wait for the response to arrive with a timeout (e.g., 10 seconds)
            payload = await asyncio.wait_for(future, timeout=2)
            # print(f"payload: {payload}")
            return payload
        except asyncio.TimeoutError:
            logger.error(f"TimeoutError reading Payload for {folder_path}")
            return None
        finally:
            # Clean up the pending request so we don't leak memory
            self.pending_requests.pop(request_id, None)

    # ------------------------------------------------------------------------------------------------------------------
    async def handle_message(self, msg):
        """
        This method should be called in your WebSocket message handler whenever a message
        is received from the child. It inspects the message for a 'request_id' and sets the result
        for the corresponding pending request.
        """
        try:
            data = json.loads(msg)
        except Exception as e:
            # Handle json decode error here if needed
            return

        type = data.get('type', None)
        print(f"Got message from child of type {type}")
        match type:
            case 'response':
                # Check if the message is a reply with a request_id that matches one of our pending requests
                request_id = data.get("request_id")
                # print(f"Request ID: {request_id}, Pending Requests: {self.pending_requests.keys()}")
                if request_id and request_id in self.pending_requests:
                    future = self.pending_requests[request_id]
                    if not future.done():
                        # You can extract the actual payload from the response as needed (e.g., data.get("payload"))
                        future.set_result(data.get("data"))
                else:
                    # Process message that are not responses to our requests
                    pass

            case 'update_widget':
                # asyncio.create_task(self.app.handle_widget_message(data, "child"))
                widget_data = data.get("data", None)
                if widget_data is not None:
                    await self.app.update_widget(widget_data)

            case 'switch_group':
                path = data.get("path", None)
                payload = data.get("payload", None)

                if path is not None:
                    self.path_in_child_app = path
                    print(f"Child App {self.id} got path: {path}")

                if self.app.active_child == self:
                    await self.app.send_to_webapps(payload)


        # if self.parent_websocket is not None:
        #     message = {
        #         'type': 'switch_group',
        #         'path': self.current_group.uid,
        #         'payload': payload,
        #     }
        #     await self.parent_websocket.send_json(message)

    # ------------------------------------------------------------------------------------------------------------------

    async def setCurrentGroup(self, path):
        message = {
            'type': 'set_current_group',
            'path': path
        }
        await self.websocket.send_json(message)
#
# # TODO:
# - send to the child that we enter this group
# - set child app group as current group
# - add a back button somehow
# - redirect the widget messages
# - handle messages in the child like "widget"
# - when recoginizing a folder button press from within the child set, we send it. Then the child sends a change_set to the parent
# - the parent then queries the child for payload?
# - i think the main idea is that the child app is synchronized to the parent app python side


# we are getting closer. I can now switch pages by clicking onto the folder on parent side, but now the child has to respond and set the new page
# But how do we determine if it is correct now to send the page change?


# ======================================================================================================================

# ======================================================================================================================

class ControlApp:
    current_group: (WidgetGroup, None)

    root_group: (WidgetGroup, None)

    children: dict[str, ControlAppChild]

    active_child: ControlAppChild

    def __init__(self, id: str, port=80, mdns_name: str = 'bilbolab', parent_address: str = None,
                 parent_port: int = 80):
        self.id = id
        self.address = None
        self.current_group = None
        self.root_group = None  # Will hold the root group.

        self.clients = set()
        self.webapp_clients = set()

        self.app = web.Application()
        self.setup_routes()

        self.loop = None  # Will hold our event loop.
        self.runner = None  # Will hold our AppRunner.

        self.port = port
        self.mdns_name = mdns_name
        self.popup_callback = None

        self.parent_address = parent_address
        self.parent_port = parent_port

        self.parent_websocket = None
        self.integrated = False

        self.children = {}

        self.active_child = None

    # ------------------------------------------------------------------------------------------------------------------
    def init(self, root_group: WidgetGroup):
        self.root_group = root_group
        self.current_group = root_group
        self.assign_app_to_tree(root_group)

    # ------------------------------------------------------------------------------------------------------------------
    def setup_routes(self):
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/ws', self.websocket_handler)
        self.app.router.add_static('/', path='../static', name='static')

        self.app.router.add_get('/info', self.info_handler)

    # ------------------------------------------------------------------------------------------------------------------
    async def info_handler(self, request):
        """
        Returns some JSON info indicating that we're alive and well,
        plus any other metadata you want to expose.
        """
        return web.json_response({
            "status": "running",
            'port': self.port,
            'address': self.address,
            # "app_name": "ControlApp",
            # "version": "1.0",
            # "current_group": self.current_group.name if self.current_group else None,
            # "path": self.current_path
        })

    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def check_target_app_is_up(target_host, target_port=80) -> (dict, None):
        url = f"http://{target_host}:{target_port}/info"
        try:
            response = requests.get(url, timeout=1.0)
            if response.status_code == 200:
                data = dict(response.json())
                # We can return True or any logic derived from data
                return data
            else:
                return None
        except requests.RequestException:
            return None

    # ------------------------------------------------------------------------------------------------------------------
    def assign_app_to_tree(self, group):
        group.app = self
        for child in group.widgets + group.groups:
            if isinstance(child, WidgetGroup):
                self.assign_app_to_tree(child)
            else:
                child.app = self

    # ------------------------------------------------------------------------------------------------------------------
    async def index(self, request):
        return web.FileResponse('../index.html')

    # ------------------------------------------------------------------------------------------------------------------
    async def websocket_handler(self, request):
        ws = web.WebSocketResponse(heartbeat=10)
        await ws.prepare(request)
        self.clients.add(ws)

        client_type = None
        client_id = None

        async for msg in ws:
            msg: WSMessage
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    if client_type is None:
                        if data.get('type') == 'handshake':
                            client_type = data.get('client', None)
                            client_id = 'web'
                            if client_type == 'web':
                                self.webapp_clients.add(ws)
                                logger.info(f"New web client connected")
                                await self.send_current_group()

                            elif client_type == 'control_app':
                                client_id = data.get('id', None)
                                asyncio.create_task(self.registerChildren(child_id=data.get('id', None),
                                                                          child_address=data.get('address', None),
                                                                          child_port=data.get('port', None),
                                                                          root_folder=data.get('root_folder', None),
                                                                          websocket=ws))

                    elif client_type == 'control_app':
                        if client_id is not None and client_id in self.children:
                            await self.children[client_id].handle_message(msg.data)

                    elif client_type == 'web':
                        match data.get('type', None):
                            case 'widget':
                                await self.handle_widget_message(data, 'web')
                            case 'navigation':
                                await self.handle_navigation_message(data, "web")
                            case 'special':
                                await self.handle_special_message(data, ws)

                except Exception as e:
                    logger.error("Error processing message:", e)
            elif msg.type == web.WSMsgType.ERROR:
                logger.error("WebSocket error:", ws.exception())

        try:
            self.clients.remove(ws)
            if client_type == 'control_app':
                self.removeChild(child_id=client_id)
            elif client_type == 'web':
                self.webapp_clients.remove(ws)
                logger.info("Removed web client")

        except Exception as e:
            logger.error("Error removing client:", e)
        return ws

    # ------------------------------------------------------------------------------------------------------------------
    async def handle_widget_message(self, data, sender):

        widget_id = data.get('id', None)

        if widget_id is None:
            logger.error("No widget id in message")
            return

        # Now this belonged to the proxy app, so redirect it
        if sender == 'web':
            if self.active_child is not None:
                asyncio.create_task(self.active_child.websocket.send_json(data))
                return

        widget = self.getByPath(widget_id)

        if widget is None:
            logger.warning(f"Widget {widget_id} not found")
            return

        logger.info(f"Handling widget message for {widget_id} of type {type(widget)}")


        # I have to update this: I already got the widget, I dont have to look for it!

        if data.get("event_type") == "button_click":
            if hasattr(widget, "on_pressed"):
                await widget.on_pressed()

        elif data.get("event_type") == "multi_state_button_click":
            if isinstance(widget, MultiStateButton):
                await widget.on_pressed()

        elif data.get("event_type") == "multi_state_button_double_click":
            if hasattr(widget, "on_double_click"):
                await widget.on_double_click()

        elif data.get("event_type") == "multi_state_button_long_click":
            if hasattr(widget, "on_long_pressed"):
                await widget.on_long_pressed()

        elif data.get("event_type") == "button_double_click":
            if hasattr(widget, "on_double_click"):
                await widget.on_double_click()

        elif data.get("event_type") == "button_long_click":
            if hasattr(widget, "on_long_pressed"):
                await widget.on_long_pressed()

        elif data.get("event_type") == "multi_select_change":
            new_value = data.get("value", None)
            if hasattr(widget, "on_value_change"):
                await widget.on_value_change(new_value)

        elif data.get("event_type") == "slider_change":
            new_value = data.get("value")

            if hasattr(widget, "on_value_changed"):
                await widget.on_value_changed(new_value)

        # New handling for JoystickWidget events
        elif data.get("event_type") == "joystick_change":
            new_x = data.get("x")
            new_y = data.get("y")
            if hasattr(widget, "on_value_changed"):
                await widget.on_value_changed(new_x, new_y)
        elif data.get("event_type") == "update_digitalnumber":
            # This is handled on the client side; no server action needed here.
            pass

        # New handling for SplitButton events
        elif data.get("event_type") == "split_button_click":
            part = data.get("part")
            if hasattr(widget, "on_part_pressed"):
                await widget.on_part_pressed(part)

        elif data.get("event_type") == "split_button_double_click":
            part = data.get("part")
            if hasattr(widget, "on_part_double_click"):
                await widget.on_part_double_click(part)

        elif data.get("event_type") == "split_button_long_click":
            button_id = data.get("id")
            part = data.get("part")
            if hasattr(widget, "on_part_long_pressed"):
                await widget.on_part_long_pressed(part)

        # New: Handle long press events from sliders, joysticks, and multi_select
        elif data.get("event_type") == "slider_long_click":
            logger.info(f"Slider {data.get('id')} long pressed.")
        elif data.get("event_type") == "joystick_long_click":
            logger.info(f"Joystick {data.get('id')} long pressed.")
        elif data.get("event_type") == "multi_select_long_click":
            logger.info(f"MultiSelect {data.get('id')} long pressed.")

        # NEW: Handle incoming popup trigger if needed.
        elif data.get("event_type") == "popup":
            # Not expected from the client.
            pass

    # ------------------------------------------------------------------------------------------------------------------
    async def handle_navigation_message(self, data, sender):

        event_type = data.get("event_type", None)

        if event_type is None:
            return

        if self.active_child is not None:
            asyncio.create_task(self.active_child.websocket.send_json(data))
            return

        match event_type:
            case "page_change":
                # New: Handle page change requests.
                if "page" in data:
                    new_page = int(data.get("page"))
                    if 0 <= new_page < self.current_group.pages:
                        self.current_group.current_page = new_page
                else:
                    direction = data.get("direction")
                    if direction == "up":
                        self.current_group.current_page = max(0, self.current_group.current_page - 1)
                    elif direction == "down":
                        self.current_group.current_page = min(self.current_group.pages - 1,
                                                              self.current_group.current_page + 1)
                # await self.broadcast_current_group()
                await self.send_current_group()

            case _:
                logger.warning(f"Unknown navigation event type: {event_type}")

    # ------------------------------------------------------------------------------------------------------------------
    async def handle_special_message(self, data, ws):
        event_type = data.get("event_type", None)

        match event_type:
            case "popup_response":
                button_id = data.get("button")
                if self.popup_callback:
                    self.popup_callback(button_id)
                    self.popup_callback = None
                    await self.broadcast({"type": "hide_popup"})
            case _:
                ...

    # ------------------------------------------------------------------------------------------------------------------
    def set_active_child(self, child):
        self.active_child = child
        logger.info(f"Active child set to {child.app_id}")

    # ------------------------------------------------------------------------------------------------------------------
    async def _broadcast_speak(self, text):
        await self.broadcast({
            "type": "speak",
            "text": text
        })

    # ------------------------------------------------------------------------------------------------------------------
    def register_to_parent(self, parent_address, parent_port=80):
        self.parent_address = parent_address
        self.parent_port = parent_port
        self.parent_websocket = None
        self.integrated = False

        self.loop.create_task(self._register_to_parent(parent_address, parent_port))

    # ------------------------------------------------------------------------------------------------------------------
    async def _register_to_parent(self, parent_address, parent_port):
        self.parent_websocket = None
        self.integrated = False
        self.parent_address = parent_address
        self.parent_port = parent_port

        while True:
            result = self.check_target_app_is_up(parent_address, parent_port)
            if result is None:
                logger.warning("Parent app is not active. Retrying in 5 seconds...")
                await asyncio.sleep(5)
                continue

            parent_address_clear = result['address']
            parent_port_clear = result['port']

            ws_url = f"ws://{parent_address_clear}:{parent_port_clear}/ws"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(ws_url, heartbeat=5) as parent_ws:
                        self.parent_websocket = parent_ws
                        logger.info(f"Connected to parent ws at {ws_url}")

                        # Send initial handshake
                        payload = {
                            'type': 'handshake',
                            'client': 'control_app',
                            'address': self.address,
                            'port': self.port,
                            'id': self.id,
                            'root_folder': self.root_group.name,
                        }
                        await self.parent_websocket.send_json(payload)

                        # Listen for messages
                        async for msg in parent_ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                await self.handle_parent_message(data)
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                logger.error("WebSocket error: %s", parent_ws.exception())
                                break
                            elif msg.type == aiohttp.WSMsgType.CLOSED:
                                logger.warning("WebSocket closed by parent.")
                                break

                        logger.info("Parent disconnected. Reconnecting in 5 seconds...")

            except Exception as e:
                logger.error("Connection to parent failed: %s", e)

            # Wait before retrying
            await asyncio.sleep(5)

    # ------------------------------------------------------------------------------------------------------------------
    async def _handle_parent_request(self, data):
        request_type = data.get('request_type', None)

        match request_type:
            case 'get_folder_payload':
                path = data.get('folder_path', None)
                folder = self.getByPath(path)
                if folder:
                    payload = await folder.get_payload()

                    answer = {
                        'type': 'response',
                        'request_id': data.get('request_id', None),
                        'data': payload,
                    }

                    await self.parent_websocket.send_json(answer)
            case _:
                logger.warning(f"Unknown request type from parent: {request_type}")

    # ------------------------------------------------------------------------------------------------------------------
    async def registerChildren(self, child_id, child_address, child_port, root_folder, websocket):

        if child_id is None or child_address is None or child_port is None:
            logger.error("Invalid child registration data.")
            return

        if child_id in self.children:
            logger.warning(f"Child {child_id} already registered.")
            return

        self.children[child_id] = ControlAppChild(child_id, child_address, child_port, root_folder, websocket, self)
        logger.info(f"Registered child {child_id} at {child_address}:{child_port}. Root folder: {root_folder}")

        self.root_group.addProxyGroup(self.children[child_id].root_group)


    # ------------------------------------------------------------------------------------------------------------------
    async def handle_parent_message(self, data):

        type = data.get("type", None)

        if type is None:
            logger.warning("Invalid message type received from parent.")

        match type:
            case 'request':
                await self._handle_parent_request(data)
            case 'set_current_group':
                group_id = data.get('path', None)
                if group_id is not None:
                    group = self.getByPath(group_id)
                    if group is not None:
                        self.setCurrentGroup(group)
                        print(f"Parent requested to set current group to {group_id}")
            case 'widget':
                print(f"Received widget message from parent: {data}")
                await self.handle_widget_message(data, "parent")
            case 'navigation':
                print(f"Received Navigation message from parent: {data}")
                await self.handle_navigation_message(data, "parent")
            case _:
                logger.warning(f"Unknown parent message type: {type}")

    # ------------------------------------------------------------------------------------------------------------------
    def removeChild(self, child_id):
        if child_id in self.children:
            del self.children[child_id]
        logger.info(f"Removed child {child_id}")

    # ------------------------------------------------------------------------------------------------------------------
    def speak(self, text):
        """
        Send a "speak" command to all connected clients, which will invoke
        the front-end's speak(...) function using the HTML5 SpeechSynthesis API.
        """
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._broadcast_speak(text), self.loop)
        else:
            asyncio.run(self._broadcast_speak(text))

    # ------------------------------------------------------------------------------------------------------------------
    async def broadcast(self, message):
        disconnected = []
        clients = self.clients.copy()
        for ws in clients:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.clients.remove(ws)

    # ------------------------------------------------------------------------------------------------------------------
    async def update_widget(self, data):
        await self.send_to_webapps(data)

        if self.parent_websocket is not None:
            msg = {
                'type': 'update_widget',
                'data': data,
            }
            await self.parent_websocket.send_json(msg)

    # ------------------------------------------------------------------------------------------------------------------
    async def send_to_webapps(self, message):
        for ws in self.webapp_clients:
            await ws.send_json(message)

    # ------------------------------------------------------------------------------------------------------------------
    def send_current_group_non_async(self):
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.send_current_group(), self.loop)
        else:
            asyncio.run(self.send_current_group())

    # ------------------------------------------------------------------------------------------------------------------
    async def send_current_group(self):
        payload = await self.current_group.get_payload()
        payload["type"] = "switch_set"
        await self.send_to_webapps(payload)

        if self.parent_websocket is not None:
            message = {
                'type': 'switch_group',
                'path': self.current_group.uid,
                'payload': payload,
            }
            await self.parent_websocket.send_json(message)

    # ------------------------------------------------------------------------------------------------------------------
    def go_back(self):
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._go_back(), self.loop)
        else:
            asyncio.run(self._go_back())

    # ------------------------------------------------------------------------------------------------------------------
    async def _go_back(self):
        if self.current_group.group is not None:
            self.setCurrentGroup(self.current_group.group)

    @property
    def current_path(self):
        return self.current_group.get_path()

    # ------------------------------------------------------------------------------------------------------------------
    def run(self, host="0.0.0.0"):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.runner = web.AppRunner(self.app)
        self.loop.run_until_complete(self.runner.setup())

        ip = getValidHostIP()
        if ip is None:
            ip = '127.0.0.1'

        self.address = ip

        site = web.TCPSite(self.runner, host="0.0.0.0", port=self.port)
        self.loop.run_until_complete(site.start())

        if self.parent_address:
            self.loop.create_task(self._register_to_parent(self.parent_address, self.parent_port))

        # Set up mDNS advertisement if Zeroconf is available.
        zeroconf_instance = None
        service_info = None
        if Zeroconf is not None:
            zeroconf_instance = Zeroconf()

            service_info = ServiceInfo(
                "_http._tcp.local.",
                f"{self.mdns_name}._http._tcp.local.",
                addresses=[socket.inet_aton(self.address)],
                port=self.port,
                properties={},
                server=f"{self.mdns_name}.local."
            )

            zeroconf_instance.register_service(service_info)
            logger.info(f"mDNS service registered as {self.mdns_name}.local (IP: {self.address}:{self.port})")
        else:
            logger.warning(f"mDNS service not registered as {self.mdns_name}.local")
        try:
            self.loop.run_forever()
        finally:
            self.loop.run_until_complete(self.runner.cleanup())
            if zeroconf_instance and service_info:
                zeroconf_instance.unregister_service(service_info)
                zeroconf_instance.close()

    # ------------------------------------------------------------------------------------------------------------------
    def run_in_thread(self, host="0.0.0.0"):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread

    # ------------------------------------------------------------------------------------------------------------------
    def close(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            logger.info("Server close requested.")

    # ------------------------------------------------------------------------------------------------------------------
    def getByPath(self, path: str):
        """
        Resolves a widget or group by absolute path. Returns None if not found.

        Accepts both:
          - path using IDs: "root/folder1/button1"
          - path using names: "Root/Folder 1/Button 1" (case- and space-insensitive)

        Automatically normalizes names to match how folder IDs are generated.
        """
        if not self.root_group:
            return None

        # Remove leading slash if present.
        if path.startswith("/"):
            path = path[1:]

        tokens = path.split("/")
        current = self.root_group

        def normalize_name(name):
            return name.lower().replace(" ", "")

        # Check that the first token matches the root group's id.
        if normalize_name(tokens[0]) != current.group_id:
            return None  # The path does not start at the root.

        # Walk through each token in the path.
        for i, token in enumerate(tokens[1:], start=1):
            token_norm = normalize_name(token)
            found = None

            # Look in the children of the current group.
            for child in current.widgets + current.groups:
                # For a group, compare group_id.
                if isinstance(child, WidgetGroup):
                    if normalize_name(child.group_id) == token_norm:
                        found = child
                        break
                # Otherwise, assume it's a widget (which should have widget_id).
                elif hasattr(child, "widget_id"):
                    if not isinstance(child.widget_id, str):
                        print(child.widget_id)
                        raise ValueError("widget_id must be a string")

                    if normalize_name(child.widget_id) == token_norm:
                        found = child
                        break

            if found is None:
                return None

            # If we're not at the last token, then only a group can have children.
            if i < len(tokens) - 1:
                if isinstance(found, WidgetGroup):
                    current = found
                else:
                    return None
            else:
                return found

        return current

    # ------------------------------------------------------------------------------------------------------------------
    async def _setCurrentGroup(self, group):
        self.current_group = group
        await self.send_current_group()

        out = f"Current Path: {self.current_path}"

        if self.active_child:
            out += f"//{self.active_child.path_in_child_app}"

        print(out)

    # ------------------------------------------------------------------------------------------------------------------
    def setCurrentGroup(self, group: WidgetGroup):
        # asyncio.create_task(self._setCurrentGroup(group))
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._setCurrentGroup(group), self.loop)
        else:
            logger.error("Event loop not initialized.")

    # ------------------------------------------------------------------------------------------------------------------
    def resetCurrentGroup(self):
        self.setCurrentGroup(self.root_group)

    # ------------------------------------------------------------------------------------------------------------------
    def in_proxy(self) -> bool:
        return isinstance(self.current_group, ChildProxyGroup)

    def get_proxy_app(self):
        return self.current_group.child_app

    # ------------------------------------------------------------------------------------------------------------------
    def show_popup(self, text, buttons, callback):
        """
        Trigger a popup on the client.
        :param text: The message text to display.
        :param buttons: List of dicts representing buttons (e.g. {"id": "ok", "label": "OK", "color": "#00AA00"}).
        :param callback: A callback function accepting the button id pressed.
        """
        self.popup_callback = callback
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._broadcast_popup(text, buttons), self.loop)
        else:
            asyncio.run(self._broadcast_popup(text, buttons))

    # ------------------------------------------------------------------------------------------------------------------
    def image_popup(self, text, image_base64, buttons, callback):
        """
        Trigger a popup on the client that displays an image along with text.
        :param text: The popup text message.
        :param image_base64: The base64-encoded PNG image string.
        :param buttons: A list of dicts representing popup buttons
                        (e.g., {"id": "ok", "label": "OK", "color": "#00AA00"}).
        :param callback: A callback function accepting the id of the button pressed.
        """
        self.popup_callback = callback
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._broadcast_image_popup(text, image_base64, buttons), self.loop)
        else:
            asyncio.run(self._broadcast_image_popup(text, image_base64, buttons))

    # ------------------------------------------------------------------------------------------------------------------
    async def _broadcast_image_popup(self, text, image_base64, buttons):
        message = {
            "type": "popup",
            "text": text,
            "image": image_base64,  # New field to carry the image data
            "buttons": buttons
        }
        await self.broadcast(message)

    # ------------------------------------------------------------------------------------------------------------------
    async def _broadcast_popup(self, text, buttons):
        message = {"type": "popup", "text": text, "buttons": buttons}
        await self.broadcast(message)
