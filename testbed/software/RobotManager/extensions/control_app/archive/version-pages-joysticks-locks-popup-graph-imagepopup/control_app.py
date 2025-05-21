import asyncio
import json
import math
import threading
import time
import socket
from aiohttp import web
from zeroconf import Zeroconf, ServiceInfo

# === CUSTOM PACKAGES ==================================================================================================
from core.utils.logging_utils import Logger
from core.utils.callbacks import callback_definition, CallbackContainer
from core.utils.network.network import getLocalAndUsbIPs, getValidHostIP


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

class Widget:
    def __init__(self, id, text, color: (str, list) = None, textcolor: (str, list) = None,
                 size=None, position=None, lockable=False, locked=False):
        self.id = id  # Unique identifier (used in paths)
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
        self.parent = None  # Will be set when added to a ButtonGroup
        self.app = None  # This will be set later (see assign_app_to_tree)
        self.callbacks = ButtonCallbacks()
        self.size = size if size is not None else (1, 1)
        self.position = position  # If None, will be auto-assigned

        self.lockable = lockable  # Only indicates if the widget can be locked
        self.locked = locked      # NEW: Determines if the widget is currently locked

    # ------------------------------------------------------------------------------------------------------------------
    async def on_pressed(self):
        self.toggle_state = not self.toggle_state
        self.callbacks.clicked.call()
        logger.debug(f"Button {self.id} pressed")

    # ------------------------------------------------------------------------------------------------------------------
    async def on_double_click(self):
        self.callbacks.double_clicked.call()
        logger.debug(f"Button {self.id} double clicked")

    # ------------------------------------------------------------------------------------------------------------------
    async def on_long_pressed(self):
        self.callbacks.long_pressed.call()
        logger.debug(f"Button {self.id} long pressed")

    # ------------------------------------------------------------------------------------------------------------------
    def get_payload(self):
        return {
            "id": self.id,
            "name": self.text,
            "color": self.color,
            "textcolor": self.textcolor,
            "is_folder": False,
            "lockable": self.lockable,    # Now only indicates whether locking is supported
            "locked": self.locked         # NEW: Indicates the current locked state
        }

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_text(self, new_text):
        self.text = new_text
        if self.app:
            await self.app.broadcast({
                "type": "update_button",
                "id": self.id,
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
            await self.app.broadcast({
                "type": "update_button",
                "id": self.id,
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
            await self.app.broadcast({
                "type": "update_button",
                "id": self.id,
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
class SplitButton(Widget):

    def __init__(self, id, split: tuple, texts: list, colors: list = None, textcolors: list = None,
                 size=None, position=None, lockable=False, locked=False):
        super().__init__(id, text="", color=None, textcolor=None, size=size, position=position, lockable=lockable, locked=locked)
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
    def get_payload(self):
        total_parts = self.split[0] * self.split[1]
        payload = {
            "id": self.id,
            "widget_type": "split_button",
            "split": self.split,
            "parts": [],
            "lockable": self.lockable,   # NEW
            "locked": self.locked         # NEW
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
        logger.debug(f"SplitButton {self.id} part {part_index} pressed")

    # ------------------------------------------------------------------------------------------------------------------
    async def on_part_double_click(self, part_index):
        self.callbacks.part_double_clicked.call(part_index)
        logger.debug(f"SplitButton {self.id} part {part_index} double clicked")

    # ------------------------------------------------------------------------------------------------------------------
    async def on_part_long_pressed(self, part_index):
        self.callbacks.part_long_pressed.call(part_index)
        logger.debug(f"SplitButton {self.id} part {part_index} long pressed")


# ======================================================================================================================
class MultiStateButton(Widget):
    def __init__(self, id, title, states, color=None, current_state=0, textcolor="#fff",
                 size=None, position=None, lockable=False, locked=False):
        super().__init__(id, title, color, textcolor, size, position, lockable=lockable, locked=locked)
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
    def get_payload(self):
        state_str, state_color = self.get_current_state_info()
        effective_color = state_color if state_color is not None else self.color
        return {
            "id": self.id,
            "name": self.text,
            "color": effective_color,
            "textcolor": self.textcolor,
            "widget_type": "multi_state_button",
            "states": self.states,
            "text": self.text,
            "current_state": self.current_state,
            "state": state_str,
            "is_folder": False,
            "lockable": self.lockable,   # NEW
            "locked": self.locked         # NEW
        }

    # ------------------------------------------------------------------------------------------------------------------
    async def on_pressed(self):
        await self._set_current_state((self.current_state + 1) % len(self.states))
        self.callbacks.clicked.call(self.current_state)
        logger.debug(f"Multi-State button {self.id} pressed. Current state: {self.current_state}")

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_current_state(self, new_state):
        self.current_state = new_state
        state_str, state_color = self.get_current_state_info()
        effective_color = state_color if state_color is not None else self.color
        if self.app:
            await self.app.broadcast({
                "type": "update_multi_state",
                "id": self.id,
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
            await self.app.broadcast({
                "type": "update_multi_state",
                "id": self.id,
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
class MultiSelectButton(Widget):
    def __init__(self, id, name, options, value, color=None, title="", textcolor="#fff",
                 size=None, position=None, lockable=False, locked=False):
        super().__init__(id, name, color, textcolor, size, position, lockable=lockable, locked=locked)
        self.options = options  # List of dicts with keys "value" and "label"
        self.value = value
        self.title = title  # Optional title displayed above the selected option
        self.callbacks = MultiSelectButtonCallbacks()

    # ------------------------------------------------------------------------------------------------------------------
    def get_payload(self):
        payload = {
            "id": self.id,
            "name": self.text,
            "color": self.color,
            "textcolor": self.textcolor,
            "widget_type": "multi_select",
            "options": self.options,
            "value": self.value,
            "is_folder": False,
            "lockable": self.lockable,   # NEW
            "locked": self.locked         # NEW
        }
        if self.title:
            payload["title"] = self.title
        return payload

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_value(self, new_value):
        self.value = new_value
        if self.app:
            await self.app.broadcast({
                "type": "update_multi_select",
                "id": self.id,
                "value": self.value
            })
        self.callbacks.value_changed.call(new_value)
        logger.debug(f"Multi-Select button {self.id} value changed to {self.value}")

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

@callback_definition
class SliderWidgetCallbacks:
    value_changed: CallbackContainer


class SliderWidget:
    def __init__(self, id, title, min_value, max_value, current_value, color, textcolor="#fff",
                 size=None, position=None, direction="horizontal", automatic_reset=None, lockable=False, locked=False):
        self.id = id
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
        self.app = None
        self.size = size if size is not None else (1, 1)
        self.position = position
        self.parent = None
        self.callbacks = SliderWidgetCallbacks()
        self.lockable = lockable    # NEW
        self.locked = locked        # NEW

    # ------------------------------------------------------------------------------------------------------------------
    def get_payload(self):
        return {
            "id": self.id,
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
            "locked": self.locked        # NEW
        }

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_value(self, new_value):
        self.value = new_value
        if self.app:
            await self.app.broadcast({
                "type": "update_slider",
                "id": self.id,
                "value": self.value
            })

        logger.debug(f"Slider button {self.id} value changed to {self.value}")

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

class JoystickWidget:
    def __init__(self, id, title, initial_x=0, initial_y=0, size=None, position=None,
                 fixed_axis=None, lockable=False, locked=False):
        self.id = id
        self.title = title
        self.x = initial_x
        self.y = initial_y
        self.app = None
        self.size = size if size is not None else (1, 1)
        self.position = position
        self.callbacks = JoystickWidgetCallbacks()
        self.lockable = lockable    # NEW
        self.locked = locked        # NEW
        # New: support fixing one axis. Valid values: "horizontal" or "vertical"
        self.fixed_axis = fixed_axis
        if fixed_axis == "horizontal":
            self.fixed_y = initial_y
        elif fixed_axis == "vertical":
            self.fixed_x = initial_x

    def get_payload(self):
        payload = {
            "id": self.id,
            "widget_type": "joystick",
            "title": self.title,
            "x": self.x,
            "y": self.y,
            "is_folder": False,
            "lockable": self.lockable,  # NEW
            "locked": self.locked        # NEW
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
        print(f"Joystick button {self.id} value changed to {self.x}, {self.y}")
        if self.app:
            await self.app.broadcast({
                "type": "update_joystick",
                "id": self.id,
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
class TextWidget:
    def __init__(self, id, title, text, color: (str, list) = None, textcolor: (str, list) = "#fff",
                 size=None, position=None, lockable=False, locked=False):
        self.id = id
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
        self.app = None
        self.size = size if size is not None else (1, 1)
        self.position = position
        self.parent = None
        self.lockable = lockable   # NEW
        self.locked = locked       # NEW

    # ------------------------------------------------------------------------------------------------------------------
    def get_payload(self):
        return {
            "id": self.id,
            "widget_type": "text",
            "title": self.title,
            "text": self.text,
            "color": self.color,
            "textcolor": self.textcolor,
            "is_folder": False,
            "lockable": self.lockable,  # NEW
            "locked": self.locked        # NEW
        }

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_text(self, new_text):
        self.text = new_text
        if self.app:
            await self.app.broadcast({
                "type": "update_text",
                "id": self.id,
                "text": self.text
            })

    # ------------------------------------------------------------------------------------------------------------------
    def set_text(self, new_text):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._set_text(new_text), self.app.event_loop)
        else:
            asyncio.run(self._set_text(new_text))


# ======================================================================================================================
class DigitalNumberWidget:
    def __init__(self, id, title, value, decimals, color, textcolor="#fff", max_digits=8,
                 size=None, position=None, lockable=False, locked=False):
        self.id = id
        self.title = title
        self.value = value
        self.decimals = decimals
        if isinstance(color, list):
            color = rgb_to_hex(color)
        if isinstance(textcolor, list):
            textcolor = rgb_to_hex(textcolor)
        self.color = color
        self.textcolor = textcolor
        self.app = None
        self.size = size if size is not None else (1, 1)
        self.position = position
        self.parent = None
        self.max_length = max_digits + 1
        self.lockable = lockable    # NEW
        self.locked = locked        # NEW

    # ------------------------------------------------------------------------------------------------------------------
    def get_payload(self):
        formatted_value = format(self.value, f".{self.decimals}f")
        return {
            "id": self.id,
            "widget_type": "digitalnumber",
            "title": self.title,
            "value": formatted_value,
            "decimals": self.decimals,
            "color": self.color,
            "textcolor": self.textcolor,
            "is_folder": False,
            "max_length": self.max_length,
            "lockable": self.lockable,  # NEW
            "locked": self.locked        # NEW
        }

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_value(self, new_value):
        self.value = new_value
        formatted_value = format(self.value, f".{self.decimals}f")
        if self.app:
            await self.app.broadcast({
                "type": "update_digitalnumber",
                "id": self.id,
                "value": formatted_value
            })

    # ------------------------------------------------------------------------------------------------------------------
    def set_value(self, new_value):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._set_value(new_value), self.app.event_loop)
        else:
            asyncio.run(self._set_value(new_value))

class GraphWidget:
    def __init__(self, id, title, y_min, y_max, window_time, color, textcolor="#fff", line_color="#00FF00", size=None, position=None, lockable=False, locked=False):
        self.id = id
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
        self.app = None
        # Minimum size for a GraphWidget is two columns wide.
        self.size = size if size is not None else (2, 1)
        self.position = position
        self.lockable = lockable
        self.locked = locked

    def get_payload(self):
        return {
            "id": self.id,
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
            "grid_size": [self.size[0], self.size[1]]
        }

    def push_value(self, value):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._push_value(value), self.app.event_loop)
        else:
            asyncio.run(self._push_value(value))

    async def _push_value(self, value):
        # Send the new data point to the client.
        await self.app.broadcast({
            "type": "push_value",
            "id": self.id,
            "value": value,
            'time': time.time(),
        })


class BackButton(Widget):

    def __init__(self, id):
        name = 'Back'
        super(BackButton, self).__init__(id, name, color=[0.5, 0.5, 0.5], textcolor=[0, 0, 0], size=(1, 1),
                                         position=(0, 1))
        self.reserved = True


class HomeButton(Widget):

    def __init__(self, id):
        name = 'Home'
        super(HomeButton, self).__init__(id, name, color=[0.5, 0.5, 0.5], textcolor=[0, 0, 0], size=(1, 1),
                                         position=(0, 0))
        self.reserved = True


class ButtonGroup:
    class PlaceholderWidget:
        def __init__(self, position):
            # position is a tuple: (column, row)
            self.position = position
            self.size = (1, 1)
            self.id = f"placeholder_{position[0]}_{position[1]}"
            # For our purposes, placeholders are marked with a flag.
            self.is_placeholder = True
            # Although placed in every cell, we do not treat them as reserved widgets.
            # Instead, _assign_position will prevent non‐reserved widgets from being
            # placed in column 0 so placeholders there can only be overwritten by reserved ones.
            self.reserved = False
            self.parent = None

        def get_payload(self):
            return {
                "widget_type": "placeholder",
                "position": [self.position[0], self.position[1]],
                "grid_size": [self.size[0], self.size[1]]
            }

    def __init__(self, name, children=None, group_type="folder", color="#55FF55", pages=1):
        self.id = name.lower().replace(" ", "")
        self.name = name
        self.pages = pages  # New: number of pages supported (default 1)
        self.current_page = 0  # New: currently visible page
        # Children will include both “real” widgets (and groups) and placeholder widgets.
        self.children = []
        self.group_type = group_type  # "folder" or "modal"
        self.color = color
        self.parent = None
        self.app = None  # To be set later

        # The grid configuration: grid_size is defined as (rows, columns) for one page.
        self.size = (1, 1)
        self.grid_size = (2, 6)  # (rows per page, columns)
        self.position = None

        # Maintain a dictionary mapping each cell coordinate (col, row) to its placeholder widget.
        self._placeholders = {}

        # If initial children are provided, add them via our add methods.
        if children is not None:
            for child in children:
                if isinstance(child, ButtonGroup):
                    self.addGroup(child)
                else:
                    self.addWidget(child)

        # Pre-populate the entire grid with placeholders across all pages.
        self._init_placeholders()

        home_button = HomeButton(id=f"home_{self.id}")
        self.addWidget(home_button)

        self.parent = None

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value
        if value is not None:
            back_button = BackButton(id=f"back_{self.id}")
            back_button.callbacks.clicked.register(self._back_button_callback)
            self.addWidget(back_button)

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
                placeholder = ButtonGroup.PlaceholderWidget((c, r))
                placeholder.parent = self
                self.children.append(placeholder)
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
        for child in self.children:
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
                if placeholder in self.children:
                    self.children.remove(placeholder)

    # ---------------------------------------------------------------------------
    def addWidget(self, widget) -> 'Widget':
        """
        Add a widget to the ButtonGroup.
        """
        widget.group = self
        self.children.append(widget)
        self._assign_position(widget)
        self._remove_placeholders_in_area(widget)
        return widget

    # ---------------------------------------------------------------------------
    def addGroup(self, group: 'ButtonGroup'):
        """
        Add a folder (another ButtonGroup instance) to this ButtonGroup.
        """
        group.parent = self
        self.children.append(group)
        self._assign_position(group)
        self._remove_placeholders_in_area(group)

    # ---------------------------------------------------------------------------
    def removeWidget(self, widget_id):
        """
        Remove a widget (not a group) by its ID.
        """
        for child in list(self.children):
            if hasattr(child, "id") and child.group_id == widget_id and not isinstance(child, ButtonGroup):
                self.children.remove(child)
                return True
        return False

    # ---------------------------------------------------------------------------
    def removeGroup(self, group_id):
        """
        Remove a ButtonGroup (i.e. a folder) by its ID.
        """
        for child in list(self.children):
            if isinstance(child, ButtonGroup) and child.id == group_id:
                self.children.remove(child)
                return True
        return False

    # ---------------------------------------------------------------------------
    def get_payload(self):
        """
        Build the payload for this group by gathering payloads from all children (widgets,
        groups, and placeholders) on the current page.
        """
        rows_per_page = self.grid_size[0]
        page_offset = self.current_page * rows_per_page
        widget_payloads = []
        for child in self.children:
            # Only include the child if its row falls in the current page.
            if child.position and not (page_offset <= child.position[1] < page_offset + rows_per_page):
                continue
            if isinstance(child, ButtonGroup):
                payload = {
                    "id": child.id,
                    "name": child.name,
                    "color": child.color,
                    "textcolor": "#fff",
                    "is_folder": True
                }
            else:
                payload = child.get_payload()
            adjusted_position = [child.position[0], child.position[1] - page_offset] if child.position else [0, 0]
            payload["position"] = adjusted_position
            payload["grid_size"] = [child.size[0], child.size[1]]
            widget_payloads.append(payload)

        return {
            "set_name": self.name,
            "group_type": self.group_type,
            "grid_size": [self.grid_size[1], self.grid_size[0]],  # [columns, rows]
            "grid_items": widget_payloads,
            "path": self.get_path(),
            "current_page": self.current_page,
            "pages": self.pages,
        }

    # ---------------------------------------------------------------------------
    def get_root(self):
        current = self
        while current.parent is not None:
            current = current.parent
        return current

    # ---------------------------------------------------------------------------
    def getButtonByPath(self, path):
        if path.startswith('/'):
            current = self.get_root()
            tokens = path.strip('/').split('/')
        elif path.startswith('./'):
            current = self
            tokens = path[2:].split('/')
        else:
            current = self
            tokens = path.split('/')

        for token in tokens:
            found = None
            for child in current.children:
                if hasattr(child, "id") and child.group_id == token:
                    found = child
                    break
            if found is None:
                return None
            if token != tokens[-1]:
                if isinstance(found, ButtonGroup):
                    current = found
                else:
                    return None
            else:
                return found
        return current

    # ---------------------------------------------------------------------------
    def get_path(self):
        if self.parent is None:
            return "/" + self.id
        else:
            return self.parent.get_path().rstrip("/") + "/" + self.id


# =============================================================================
# MyApp Class Definition
# =============================================================================

class ControlApp:
    current_group: (ButtonGroup, None)

    def __init__(self, port=80, mdns_name: str = 'bilbolab'):
        self.current_group = None
        self.root_group = None  # Will hold the root group.

        self.clients = set()
        self.app = web.Application()
        self.setup_routes()

        self.loop = None  # Will hold our event loop.
        self.runner = None  # Will hold our AppRunner.

        self.port = port
        self.mdns_name = mdns_name
        # NEW: For popup functionality.
        self.popup_callback = None

    # ------------------------------------------------------------------------------------------------------------------
    def init(self, root_group: ButtonGroup):
        self.root_group = root_group
        self.current_group = root_group
        self.assign_app_to_tree(root_group)

    # ------------------------------------------------------------------------------------------------------------------
    def setup_routes(self):
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/ws', self.websocket_handler)
        self.app.router.add_static('/', path='static', name='static')

    # ------------------------------------------------------------------------------------------------------------------
    def assign_app_to_tree(self, group):
        group.app = self
        for child in group.widgets:
            if isinstance(child, ButtonGroup):
                self.assign_app_to_tree(child)
            else:
                child.app = self

    # ------------------------------------------------------------------------------------------------------------------
    async def index(self, request):
        return web.FileResponse('index.html')

    # ------------------------------------------------------------------------------------------------------------------
    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        logger.info(f"New client connected: {ws}")
        await self.send_current_group(ws)

        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    if data.get("type") == "button_click":
                        button_id = data.get("id")
                        clicked = None
                        for child in self.current_group.widgets:
                            if hasattr(child, "id") and child.group_id == button_id:
                                clicked = child
                                break
                        if clicked is None:
                            logger.warning("Clicked button not found:", button_id)
                        else:
                            if isinstance(clicked, ButtonGroup):
                                self.setCurrentGroup(clicked)
                            elif isinstance(clicked, Widget):
                                await clicked.on_pressed()
                                if self.current_group.group_type == "modal" and self.current_group.group:
                                    await self._go_back()
                            await self.broadcast({"type": "log", "message": f"Button {button_id} pressed."})

                    elif data.get("type") == "multi_state_button_click":
                        button_id = data.get("id")
                        for child in self.current_group.widgets:
                            if hasattr(child, "id") and child.group_id == button_id:
                                if isinstance(child, MultiStateButton):
                                    await child.on_pressed()
                                    break
                    elif data.get("type") == "multi_state_button_double_click":
                        button_id = data.get("id")
                        for child in self.current_group.widgets:
                            if hasattr(child, "id") and child.group_id == button_id:
                                await child.on_double_click()
                    elif data.get("type") == "multi_state_button_long_click":
                        button_id = data.get("id")
                        for child in self.current_group.widgets:
                            if hasattr(child, "id") and child.group_id == button_id:
                                await child.on_long_pressed()
                                break
                    elif data.get("type") == "button_double_click":
                        button_id = data.get("id")
                        for child in self.current_group.widgets:
                            if hasattr(child, "id") and child.group_id == button_id:
                                if isinstance(child, Widget) and not isinstance(child, MultiStateButton):
                                    await child.on_double_click()
                                break
                    elif data.get("type") == "button_long_click":
                        button_id = data.get("id")
                        for child in self.current_group.widgets:
                            if hasattr(child, "id") and child.group_id == button_id:
                                if isinstance(child, Widget) and not isinstance(child, MultiStateButton):
                                    await child.on_long_pressed()
                                break
                    elif data.get("type") == "multi_select_change":
                        button_id = data.get("id")
                        new_value = data.get("value")
                        updated = False
                        for child in self.current_group.widgets:
                            if hasattr(child, "id") and child.group_id == button_id:
                                if hasattr(child, "value"):
                                    await child.on_value_change(new_value)
                                    updated = True
                                    break
                        if not updated:
                            logger.warning("MultiSelectButton not found:", button_id)

                    elif data.get("type") == "slider_change":
                        button_id = data.get("id")
                        new_value = data.get("value")
                        updated = False
                        for child in self.current_group.widgets:
                            if hasattr(child, "id") and child.group_id == button_id:
                                if isinstance(child, SliderWidget):
                                    await child.on_value_changed(new_value)
                                    updated = True
                                    break
                        if not updated:
                            logger.warning("SliderWidget not found:", button_id)
                    # New handling for JoystickWidget events
                    elif data.get("type") == "joystick_change":
                        button_id = data.get("id")
                        new_x = data.get("x")
                        new_y = data.get("y")
                        updated = False
                        for child in self.current_group.widgets:
                            if hasattr(child, "id") and child.group_id == button_id:
                                if isinstance(child, JoystickWidget):
                                    await child.on_value_changed(new_x, new_y)
                                    updated = True
                                    break
                        if not updated:
                            logger.warning("Joystick widget not found:", button_id)
                    elif data.get("type") == "update_digitalnumber":
                        # This is handled on the client side; no server action needed here.
                        pass

                    elif data.get("type") == "get_by_path":
                        path = data.get("path")
                        button_obj = self.current_group.getButtonByPath(path)
                        if button_obj:
                            if isinstance(button_obj, Widget):
                                result = button_obj.get_payload()
                            else:
                                result = {"id": button_obj.group_id, "name": button_obj.name, "color": button_obj.color,
                                          "is_folder": True}
                        else:
                            result = None
                        await ws.send_json({"type": "path_lookup", "result": result})

                    elif data.get("type") == "page_change":
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
                        await self.broadcast_current_group()

                    # New handling for SplitButton events
                    elif data.get("type") == "split_button_click":
                        button_id = data.get("id")
                        part = data.get("part")
                        for child in self.current_group.widgets:
                            if hasattr(child, "id") and child.group_id == button_id:
                                if isinstance(child, SplitButton):
                                    await child.on_part_pressed(part)
                                    break
                    elif data.get("type") == "split_button_double_click":
                        button_id = data.get("id")
                        part = data.get("part")
                        for child in self.current_group.widgets:
                            if hasattr(child, "id") and child.group_id == button_id:
                                if isinstance(child, SplitButton):
                                    await child.on_part_double_click(part)
                                    break
                    elif data.get("type") == "split_button_long_click":
                        button_id = data.get("id")
                        part = data.get("part")
                        for child in self.current_group.widgets:
                            if hasattr(child, "id") and child.group_id == button_id:
                                if isinstance(child, SplitButton):
                                    await child.on_part_long_pressed(part)
                                    break

                    # New: Handle long press events from sliders, joysticks, and multi_select
                    elif data.get("type") == "slider_long_click":
                        logger.info(f"Slider {data.get('id')} long pressed.")
                    elif data.get("type") == "joystick_long_click":
                        logger.info(f"Joystick {data.get('id')} long pressed.")
                    elif data.get("type") == "multi_select_long_click":
                        logger.info(f"MultiSelect {data.get('id')} long pressed.")

                    # NEW: Handle popup response. When a popup button is pressed on the client,
                    # the client sends a "popup_response" message with the button id.
                    elif data.get("type") == "popup_response":
                        button_id = data.get("button")
                        if self.popup_callback:
                            self.popup_callback(button_id)
                            self.popup_callback = None
                            await self.broadcast({"type": "hide_popup"})

                    # NEW: Handle incoming popup trigger if needed.
                    elif data.get("type") == "popup":
                        # Not expected from the client.
                        pass

                except Exception as e:
                    logger.error("Error processing message:", e)
            elif msg.type == web.WSMsgType.ERROR:
                logger.error("WebSocket error:", ws.exception())

        try:
            self.clients.remove(ws)
            logger.info("Client disconnected")
        except Exception as e:
            logger.error("Error removing client:", e)
        return ws

    # ------------------------------------------------------------------------------------------------------------------
    async def handle_widget_message(self, message):
        ...

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
    async def send_current_group(self, ws):
        payload = self.current_group.get_payload()
        payload["type"] = "switch_set"
        await ws.send_json(payload)

    # ------------------------------------------------------------------------------------------------------------------
    async def broadcast_current_group(self):
        payload = self.current_group.get_payload()
        payload["type"] = "switch_set"
        await self.broadcast(payload)

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

        site = web.TCPSite(self.runner, host=host, port=self.port)
        self.loop.run_until_complete(site.start())

        # Set up mDNS advertisement if Zeroconf is available.
        zeroconf_instance = None
        service_info = None
        if Zeroconf is not None:
            zeroconf_instance = Zeroconf()
            ip = getValidHostIP()

            if ip is None:
                ip = '127.0.0.1'

            service_info = ServiceInfo(
                "_http._tcp.local.",
                f"{self.mdns_name}._http._tcp.local.",
                addresses=[socket.inet_aton(ip)],
                port=self.port,
                properties={},
                server=f"{self.mdns_name}.local."
            )

            zeroconf_instance.register_service(service_info)
            logger.info(f"mDNS service registered as {self.mdns_name}.local (IP: {ip}:{self.port})")
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

    # =============================================================================
    # New methods for external group control and popup functionality
    # =============================================================================

    async def _setCurrentGroup(self, group):
        self.current_group = group
        await self.broadcast_current_group()
        print(f"Current Path: {self.current_path}")

    def setCurrentGroup(self, group: ButtonGroup):
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._setCurrentGroup(group), self.loop)
        else:
            logger.error("Event loop not initialized.")

    def resetCurrentGroup(self):
        self.setCurrentGroup(self.root_group)

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

    async def _broadcast_image_popup(self, text, image_base64, buttons):
        message = {
            "type": "popup",
            "text": text,
            "image": image_base64,  # New field to carry the image data
            "buttons": buttons
        }
        await self.broadcast(message)

    async def _broadcast_popup(self, text, buttons):
        message = {"type": "popup", "text": text, "buttons": buttons}
        await self.broadcast(message)


# =============================================================================
# Main Execution
# =============================================================================

def example():
    app_instance = ControlApp(port=80, mdns_name='bilbolab')

    root_group = ButtonGroup("Root", group_type="folder", pages=3)
    root_group.addWidget(Widget("btn1", "Button ❌", [1, 1, 1], textcolor=[1, 0, 0], lockable=True, locked=True))
    root_group.addWidget(Widget("btn2", "Button 2", "#5555FF"))
    mode_btn = root_group.addWidget(MultiStateButton("msb2",
                                                     "Control Mode",
                                                     color="#FF5555",
                                                     states=[('off', [1, 0, 0]), ("balancing", [0, 0.8, 1])],
                                                     current_state=0))

    # Create a GraphWidget instance.
    graph_widget = GraphWidget("graph1",
                               "Real-Time Graph",
                               y_min=0,
                               y_max=100,
                               window_time=5,  # 10 seconds rolling window
                               color="#222222",
                               textcolor="#FFFFFF",
                               line_color="#FF5500",
                               size=(3, 2),
                               position=(1,4))  # minimum 2 columns wide
    # Add the graph to one of your groups (e.g., root_group or folder1)
    root_group.addWidget(graph_widget)

    folder1 = ButtonGroup("Folder 1", group_type="folder", color="#55FF55", pages=3)

    # Example: A slider widget that is lockable (locked).
    slider_widget = SliderWidget("slider1", "Volume", 0, 100, 50, "#0077CC", textcolor="#FFFFFF", size=(3, 1), lockable=True, locked=False)
    folder1.addWidget(slider_widget)

    btn1 = folder1.addWidget(Widget("f1btn1", "Folder Btn 1", "#FFAA00"))
    folder1.addWidget(Widget("f1btn2", "Folder Btn 2", "#AAFF00", textcolor=[0, 0, 0]))
    folder1.addWidget(Widget("f1btn3", "Folder Btn 3", "#FF00AA"))

    # Example: Create a folder with two pages (instead of default one)
    folder2 = ButtonGroup("Folder 2", group_type="folder", color="#55FF55", pages=5)
    folder2.addWidget(Widget("f2btn1", "Folder Btn 1", "#FFAA00", size=(3, 2), position=(1, 0)))
    folder2.addWidget(Widget("f2btn2", "Folder Btn 1", "#FFAA00", size=(1, 2)))
    folder2.addWidget(SliderWidget("slider1", "Volume", 0, 100, 50, "#0077CC", textcolor="#FFFFFF", size=(1, 2)))

    folder2.addWidget(Widget("f2btn1", "Folder Btn 1", "#FFAA00", size=(1, 1), position=(1, 2)))
    folder2.addWidget(SliderWidget("slider2", "Volume", 0, 100, 50, "#0077CC", textcolor="#FFFFFF", size=(5, 2)))
    folder1.addGroup(folder2)

    # Example: Create a SplitButton split into 3x2 parts.
    split_btn = SplitButton(
        "split1",
        split=(3, 2),
        texts=["A", "B", "C", "D", "E", "F"],
        colors=["#AA00AA","#00AAAA", "#00AAAA","#AA00AA","#00AAAA", "#00AAAA"],
        textcolors=["#FFFFFF","#000000", "#000000","#FFFFFF","#000000", "#000000"],
        size=(4, 2)
    )
    folder1.addWidget(split_btn)

    btn1.callbacks.clicked.register(lambda: logger.info("Button 1 clicked!"))
    btn1.callbacks.double_clicked.register(lambda: logger.info("Button 1 double clicked!"))
    btn1.callbacks.long_pressed.register(lambda: logger.info("Button 1 long pressed!"))

    multi_state_btn = MultiStateButton("msb1", "MultiState", color="#00AAFF",
                                       states=["Off", "On", "Auto"], current_state=0)
    folder1.addWidget(multi_state_btn)

    # Example: A multi-select widget that is lockable (locked).
    dropdown_widget = MultiSelectButton("select1", "Select Option", color="#FFAA55",
                                        options=[
                                            {"value": "1", "label": "Option 1"},
                                            {"value": "2", "label": "Option 2"},
                                            {"value": "3", "label": "Option 3"}
                                        ],
                                        value="1",
                                        title="SOPTION",
                                        size=(2, 1), lockable=True, locked=False)
    folder1.addWidget(dropdown_widget)

    # New DigitalNumberWidget instance added to the example.
    digital_number = DigitalNumberWidget("dig1",
                                         "Temperature",
                                         123456,
                                         2,
                                         "#0000FF",
                                         max_digits=8,
                                         textcolor="#FFFFFF",
                                         size=(1, 1))
    root_group.addWidget(digital_number)

    # New: Add a Joystick widget example that is lockable (locked) and fixes its vertical movement (only moves horizontally).
    joystick = JoystickWidget("joy1", "JSA", 0, 0, size=(1, 1), fixed_axis="vertical", lockable=True, locked=True)
    # Another joystick without fixed axis:
    joystick2 = JoystickWidget("joy2", "JSB", 0, 0, size=(2, 2),fixed_axis="horizontal", position=(4, 2))
    root_group.addWidget(joystick)
    root_group.addWidget(joystick2)
    # root_group.addWidget(
    #     TextWidget('txt1', "Control State. This is a long", "cbhdbvhjbvb bvfhdbvhdfb bvdhfbjcidc cjidscnjsdk cnjd", color=[0.8, 0.8, 0.8], textcolor=[0, 0, 0], size=(2,2)))
    root_group.addGroup(folder1)

    modal_group = ButtonGroup("Modal", group_type="modal", color="#888888")
    modal_group.addWidget(Widget("yes", "Yes", "#00AA00"))
    modal_group.addWidget(Widget("no", "No", "#AA0000"))

    sliders_folder = ButtonGroup("Sliders", group_type="folder", color="#FF00FF")
    slider_h = SliderWidget("slider_h", "Horizontal Slider", -100, 100, 0, "#00CC00", textcolor="#FFFFFF",
                            size=(2, 2), direction="vertical", automatic_reset=0)
    slider_v = SliderWidget("slider_v", "Vertical Slider", -100, 100, 0, "#CC0000", textcolor="#FFFFFF",
                            position=(4, 0), size=(2, 2), direction="horizontal", automatic_reset=0)
    sliders_folder.addWidget(slider_h)
    sliders_folder.addWidget(slider_v)

    xx = MultiSelectButton("select1", "Select Option", color="#FFAA55",
                           options=[
                               {"value": "0", "label": "None"},
                               {"value": "2", "label": "bilbo1"},
                               {"value": "3", "label": "bilbo2"}
                           ],
                           value="1",
                           title="SOPTION",
                           size=(1, 1))
    sliders_folder.addWidget(xx)
    root_group.addGroup(sliders_folder)

    app_instance.init(root_group)

    app_instance.modal_group = modal_group
    app_instance.multi_state_btn = multi_state_btn

    app_instance.run_in_thread()

    # NEW: Trigger a popup after 10 seconds.
    def trigger_popup():
        time.sleep(10)
        def popup_callback(button_id):
            logger.info(f"Popup button pressed: {button_id}")
        # Example: popup with one OK button.
        popup_buttons = [
            {"id": "yes", "label": "yes", "color": "#00AA00"},
            # {"id": "no", "label": "no", "color": "#00AA00"},
            # {"id": "no2", "label": "okayzi", "color": "#00AA00"}

        ]
        app_instance.show_popup("This is a popup message. ABCbhvbjhbfdjhbvjhdbfvjhbvhjbdfhvb\n This is a second line", popup_buttons, popup_callback)

    def trigger_image_popup():
        import io, base64
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
        # Create a simple plot.
        x = np.linspace(0, 2 * np.pi, 100)
        y = np.sin(x)
        plt.figure(figsize=(4,2))
        plt.plot(x, y)
        plt.title("Sine Wave")
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        # Define a callback function for popup button response.
        def popup_callback(button_id):
            logger.info(f"Image popup button pressed: {button_id}")
        popup_buttons = [
            {"id": "ok", "label": "OK", "color": "#00AA00"}
        ]

        time.sleep(10)
        app_instance.image_popup("Here is an image popup with a plot:", img_base64, popup_buttons, popup_callback)

    threading.Thread(target=trigger_image_popup, daemon=True).start()


    # threading.Thread(target=trigger_popup, daemon=True).start()

    btn1 = root_group.getButtonByPath("./folder1/f1btn2")

    # Start a separate thread that pushes data into the graph periodically.
    def push_graph_data():
        import math, time
        t = 0
        while True:
            value = 40 * math.sin(t) + 40
            graph_widget.push_value(value)
            t += 0.1
            time.sleep(0.1)

    threading.Thread(target=push_graph_data, daemon=True).start()

    try:
        t = 0  # Time variable
        while True:
            value = 80 * math.sin(t)  # Sinusoidal value between -100 and 100
            # digital_number.set_value(value)
            t += 0.05  # Increase time step
            time.sleep(0.05)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        app_instance.close()


if __name__ == '__main__':
    example()
