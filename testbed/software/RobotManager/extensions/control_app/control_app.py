from __future__ import annotations
import asyncio
import contextlib
import json
import os
import threading
import time
import socket
import uuid
from abc import ABC, abstractmethod
import re
from typing import Optional, Callable
import aiohttp
from aiohttp import web, WSMessage, TCPConnector, ClientSession
from aiohttp.web_request import Request
from zeroconf import Zeroconf, ServiceInfo

# === CUSTOM PACKAGES ==================================================================================================
from core.utils.logging_utils import Logger
from core.utils.callbacks import callback_definition, CallbackContainer
from core.utils.mdns import MDNSResolver
from core.utils.network.network import getValidHostIP
from core.utils.paths import is_subpath

ALLOW_FIRST_COLUMN_ON_SUBSEQUENT_PAGES = True


# === UTILITIES
def cut_before_folder(path: str, foldername: str) -> str:
    # Use partition to split at the first occurrence of the folder name
    before, sep, after = path.partition(foldername)
    if sep:  # if a folder name is found
        return f'/{sep}{after}'
    else:
        return path  # or raise an error if folder name not found


def prepend_parent_path(child_path: str, parent_path: str) -> str:
    # Normalize input paths by removing leading/trailing slashes
    child_parts = child_path.strip('/').split('/')
    parent_parts = parent_path.strip('/').split('/')

    if not child_parts:
        return '/' + '/'.join(child_parts)  # Just in case it's empty

    # Identify the first segment in the child (usually a root, e.g., 'child:rootz')
    root_segment = child_parts[0]

    # Try to locate this root segment in the parent path
    try:
        index = parent_parts.index(root_segment)
    except ValueError:
        return '/' + '/'.join(child_parts)  # No match found, return normalized child path

    # Build the prefix path from the parent up to the root_segment (inclusive or exclusive)
    prefix_parts = parent_parts[:index]  # up to but not including the matched segment

    # Create the new path by prepending the prefix
    new_path_parts = prefix_parts + child_parts
    return '/' + '/'.join(new_path_parts)


def rgb_to_hex(rgb):
    """
    Convert a list of RGB(A) values (0–1 floats) to a hex HTML color.
    Examples:
      rgb_to_hex([0.5, 0.2, 0.8])       -> "#8033cc"
      rgb_to_hex([0.5, 0.2, 0.8, 0.3])  -> "#8033cc4d"
    """

    def clamp(x):
        return max(0, min(x, 1))

    if len(rgb) == 3 or len(rgb) == 4:
        # clamp & scale
        comps = [int(clamp(c) * 255) for c in rgb]
        # format RGB
        hex_str = "#{:02x}{:02x}{:02x}".format(*comps[:3])
        # if alpha present, append as two hex digits
        if len(comps) == 4:
            hex_str += "{:02x}".format(comps[3])
        return hex_str

    # fallback on bad input
    return "#FFFFFF"


# GROUP_GRID_SIZE = (6, 2)
GROUP_GRID_SIZE = (2, 7)

logger = Logger('Control App')
logger.setLevel('DEBUG')


@callback_definition
class WidgetCallbacks:
    clicked: CallbackContainer


class Widget(ABC):
    widget_id: str
    uid: str

    group: WidgetGroup
    app: ControlApp

    position: dict
    size: tuple
    lockable: bool
    locked: bool
    callbacks: WidgetCallbacks

    hidden: bool

    def __init__(self, widget_id, position=None, size=None, lockable=False, locked=False, hidden=False):
        self.widget_id = widget_id
        self.position = position

        if isinstance(position, tuple):
            row, col = position
            if isinstance(col, int) and isinstance(row, int):
                self.position = {'page': None, 'column': col, 'row': row}
        elif isinstance(position, dict):
            # fill missing keys with None
            self.position = {
                "page": position.get("page"),
                "row": position.get("row"),
                "column": position.get("column")
            }
        else:
            self.position = None

        self.size = size if size else (1, 1)
        self.lockable = lockable
        self.locked = locked
        self.group = None  # type: ignore
        self.app = None  # type: ignore
        self.hidden = hidden
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
            parent = parent.parent_group
        return f"/{uid}"


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

    def __init__(self, widget_id, text, icon: str = None, icon_position: str = 'center', color: (str, list) = None,
                 textcolor: (str, list) = None,
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

        assert icon_position in ['center', 'top']

        self.color = color  # Button background color
        self.textcolor = textcolor
        self.icon = icon
        self.icon_position = icon_position
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
            "locked": self.locked,  # NEW: Indicates the current locked state,
            'hidden': self.hidden,
            "icon": self.icon,
            "icon_position": self.icon_position,
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
            "locked": self.locked,  # NEW,
            'hidden': self.hidden,
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
        super().__init__(widget_id, text=title, color=color, textcolor=textcolor, size=size, position=position,
                         lockable=lockable, locked=locked)
        self.states = states  # Can be a list of strings or tuples (state, color)
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
            "locked": self.locked,  # NEW
            'hidden': self.hidden,
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
        super().__init__(widget_id, text=name, color=color, textcolor=textcolor, size=size, position=position,
                         lockable=lockable, locked=locked)
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
            "locked": self.locked,  # NEW
            'hidden': self.hidden,
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


# ======================================================================================================================
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
class EditableValueWidgetCallbacks:
    value_changed: CallbackContainer


class EditableValueWidget(Widget):
    callbacks: EditableValueWidgetCallbacks

    def __init__(self,
                 widget_id: str,
                 title: str,
                 value: str,
                 input_validation_function: callable = None,
                 is_numeric=False,
                 color=None,
                 textcolor=None,
                 size=None,
                 position=None,
                 lockable=False,
                 locked=False,
                 hidden=False):
        super().__init__(
            widget_id,
            position=position,
            size=size,
            lockable=lockable,
            locked=locked,
            hidden=hidden,
        )
        if isinstance(color, (list, tuple)):
            color = rgb_to_hex(color)

        if isinstance(textcolor, (list, tuple)):
            textcolor = rgb_to_hex(textcolor)

        self.color = color
        self.textcolor = textcolor
        self.title = title
        self.value = value
        self.is_numeric = is_numeric
        self.input_validation_function = input_validation_function
        self.callbacks = EditableValueWidgetCallbacks()

    async def get_payload(self):
        return {
            "id": self.uid,
            "widget_type": "editable_value",
            "title": self.title,
            "value": self.value,
            "is_folder": False,
            "lockable": self.lockable,
            "locked": self.locked,
            "hidden": self.hidden,
            "color": self.color,
            "is_numeric": self.is_numeric,
        }

    async def _set_value(self, new_value: str):
        if new_value == self.value:
            return

        if self.input_validation_function is not None:
            new_value = self.input_validation_function(new_value, self.value)

        self.value = new_value
        if self.app:
            await self.app.update_widget({
                "type": "update_editable_value",
                "id": self.uid,
                "value": self.value
            })
        self.callbacks.value_changed.call(self.value)
        logger.debug(f"Editable value {self.uid} value changed to {self.value}")

    def set_value(self, new_value: str):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._set_value(new_value), self.app.event_loop)
        else:
            asyncio.run(self._set_value(new_value))

    async def on_value_changed(self, new_value: str):
        await self._set_value(new_value)


# ======================================================================================================================
@callback_definition
class RotaryDialWidgetCallbacks:
    value_changed: CallbackContainer


class RotaryDialWidget(Widget):
    callbacks: RotaryDialWidgetCallbacks

    def __init__(self,
                 widget_id: str,
                 title: str,
                 min_value: float,
                 max_value: float,
                 current_value: float,
                 value_type: str = "float",
                 precision: int = 2,
                 continuous_updates: bool = False,
                 ticks: list[float] | None = None,
                 limit_to_ticks: bool = False,
                 dial_color: str | list = None,
                 color: str | list = None,
                 size=None,
                 position=None,
                 lockable=False,
                 locked=False,
                 hidden=False):
        super().__init__(
            widget_id,
            position=position,
            size=size,
            lockable=lockable,
            locked=locked,
            hidden=hidden,
        )

        if isinstance(color, (list, tuple)):
            color = rgb_to_hex(color)

        self.color = color

        self.title = title
        self.min = min_value
        self.max = max_value
        self.value = current_value
        self.ticks = ticks or []
        self.continuous_updates = continuous_updates
        self.limit_to_ticks = limit_to_ticks

        assert value_type in ["float", "int"]
        self.value_type = value_type

        if self.value_type == "int":
            precision = 0

        self.precision = precision

        if isinstance(dial_color, (list, tuple)):
            dial_color = rgb_to_hex(dial_color)

        self.dial_color = dial_color

        self.callbacks = RotaryDialWidgetCallbacks()

    async def get_payload(self):
        return {
            "id": self.uid,
            "widget_type": "rotary_dial",
            "title": self.title,
            "min": self.min,
            "max": self.max,
            "value": self.value,
            "ticks": self.ticks,
            "is_folder": False,
            "lockable": self.lockable,
            "locked": self.locked,
            "dial_color": self.dial_color,
            "hidden": self.hidden,
            "value_type": self.value_type,
            "precision": self.precision,
            "continuous_updates": self.continuous_updates,
            "limit_to_ticks": self.limit_to_ticks,
            "color": self.color,
        }

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_value(self, new_value: float):
        # enforce type / precision
        if self.value_type == "int":
            new_value = int(round(new_value))
        else:
            new_value = round(new_value, self.precision)
        # clamp
        clamped = max(self.min, min(self.max, new_value))
        if clamped == self.value:
            return
        self.value = clamped
        if self.app:
            await self.app.update_widget({
                "type": "update_rotary_dial",
                "id": self.uid,
                "value": self.value
            })
        self.callbacks.value_changed.call(self.value)
        logger.debug(f"RotaryDial {self.uid} value changed to {self.value}")

    # ------------------------------------------------------------------------------------------------------------------
    def set_value(self, new_value: float):
        if self.app and self.app.event_loop:
            asyncio.run_coroutine_threadsafe(self._set_value(new_value), self.app.event_loop)
        else:
            asyncio.run(self._set_value(new_value))

    # ------------------------------------------------------------------------------------------------------------------
    async def on_value_changed(self, new_value: float):
        await self._set_value(new_value)


# ======================================================================================================================
@callback_definition
class IframeWidgetCallbacks:
    clicked: CallbackContainer


class IframeWidget(Widget):
    """
    A widget that displays the content of a URL in an <iframe>.
    Clicks on the widget will fire the 'clicked' callback.
    """
    callbacks: IframeWidgetCallbacks

    def __init__(self,
                 widget_id: str,
                 url: str,
                 size: tuple | None = None,
                 position: dict | None = None,
                 lockable: bool = False,
                 locked: bool = False,
                 hidden: bool = False):
        super().__init__(widget_id,
                         position=position,
                         size=size,
                         lockable=lockable,
                         locked=locked,
                         hidden=hidden)
        self.url = url
        self.callbacks = IframeWidgetCallbacks()

    async def get_payload(self):
        return {
            "id": self.uid,
            "widget_type": "iframe",
            "url": self.url,
            "lockable": self.lockable,
            "locked": self.locked,
            "hidden": self.hidden,
            "is_folder": False,
        }

    async def on_pressed(self):
        # fire the clicked callback
        self.callbacks.clicked.call()
        logger.debug(f"IframeWidget {self.uid} clicked")


# ======================================================================================================================
@callback_definition
class SliderWidgetCallbacks:
    value_changed: CallbackContainer


# ======================================================================================================================
class SliderWidget(Widget):
    callbacks: SliderWidgetCallbacks

    def __init__(self, widget_id,
                 title,
                 min_value,
                 max_value,
                 current_value,
                 value_type: str = "float",
                 precision: int = 2,
                 continuous_updates: bool = False,
                 ticks: list[float] | None = None,
                 limit_to_ticks: bool = False,
                 color="#101010",
                 textcolor="#fff",
                 size=None,
                 position=None,
                 direction="horizontal",
                 automatic_reset=None,
                 lockable=False,
                 locked=False):

        super(SliderWidget, self).__init__(widget_id, position=position, size=size, lockable=lockable, locked=locked)

        self.title = title
        self.min = min_value
        self.max = max_value
        self.value = current_value
        self.direction = direction  # "horizontal" (default) or "vertical"
        self.automatic_reset = automatic_reset  # Value to reset to when dragging is released
        self.continuous_updates = continuous_updates
        self.limit_to_ticks = limit_to_ticks

        assert value_type in ["float", "int"]

        self.value_type = value_type

        if self.value_type == "int":
            precision = 0

        self.precision = precision
        self.ticks = ticks or []

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
            "locked": self.locked,  # NEW
            'hidden': self.hidden,
            "value_type": self.value_type,
            "precision": self.precision,
            "ticks": self.ticks,
            "continuous_updates": self.continuous_updates,
            "limit_to_ticks": self.limit_to_ticks,
        }

    # ------------------------------------------------------------------------------------------------------------------
    async def _set_value(self, new_value):
        if isinstance(new_value, str):
            if self.value_type == "float":
                new_value = float(new_value)
            elif self.value_type == "int":
                new_value = int(new_value)

        # enforce type / precision
        if self.value_type == "int":
            new_value = int(round(new_value))
        else:
            new_value = round(new_value, self.precision)
        # clamp
        clamped = max(self.min, min(self.max, new_value))
        if clamped == self.value:
            return
        self.value = clamped
        if self.app:
            await self.app.update_widget({
                "type": "update_slider",
                "id": self.uid,
                "value": self.value
            })
        logger.debug(f"Slider {self.uid} value changed to {self.value}")
        # fire callbacks
        self.callbacks.value_changed.call(self.value)

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


# ======================================================================================================================
@callback_definition
class JoystickWidgetCallbacks:
    value_changed: CallbackContainer


# ======================================================================================================================
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
            "locked": self.locked,  # NEW
            'hidden': self.hidden,
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
        # print(f"Joystick button {self.uid} value changed to {self.x}, {self.y}")

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
            "locked": self.locked,  # NEW
            'hidden': self.hidden,
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
    def __init__(self, widget_id, title, value, decimals, color=None, textcolor="#fff", max_digits=8,
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
            "locked": self.locked,  # NEW
            'hidden': self.hidden,
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


# ======================================================================================================================
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
            'hidden': self.hidden,
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


# ======================================================================================================================
class SmallWidget(Widget):
    grid_widget: GridWidget

    def __init__(self, widget_id, color="#101010", textcolor="#fff", size=None, position=None,
                 lockable=False, locked=False):
        super(SmallWidget, self).__init__(widget_id, position=position, size=size, lockable=lockable, locked=locked)

        self.grid_widget = None  # type: ignore

    @abstractmethod
    def update(self):
        ...


# ======================================================================================================================
class SmallWidgetButton(SmallWidget):
    def __init__(self, widget_id, text, color="#101010", textcolor="#fff", size=None, position=None,
                 lockable=False, locked=False):
        super(SmallWidgetButton, self).__init__(widget_id, position=position, size=size, lockable=lockable,
                                                locked=locked)

        if isinstance(color, list):
            color = rgb_to_hex(color)
        if isinstance(textcolor, list):
            textcolor = rgb_to_hex(textcolor)
        self.color = color
        self.textcolor = textcolor
        self.text = text

    async def get_payload(self):
        payload = {
            'widget_type': 'small_widget_text',
            'widget_id': self.widget_id,
            'data': {
                'position': self.position,
                'size': self.size,
                'text': self.text,
                'color': self.color,
                'textcolor': self.textcolor,
            }
        }
        return payload

    def update(self, text=None, color=None, textcolor=None):
        self.text = text if text else self.text
        self.color = color if color else self.color
        self.textcolor = textcolor if textcolor else self.textcolor

    async def on_pressed(self):
        ...


# ----------------------------------------------------------------------------------------------------------------------
class SmallWidgetText(SmallWidget):
    def __init__(self, widget_id, text, font_size, color="#101010", textcolor="#fff", size=None, position=None,
                 lockable=False, locked=False):
        super(SmallWidgetText, self).__init__(widget_id, position=position, size=size, lockable=lockable, locked=locked)

        if isinstance(color, list):
            color = rgb_to_hex(color)
        if isinstance(textcolor, list):
            textcolor = rgb_to_hex(textcolor)
        self.text = text
        self.font_size = font_size
        self.color = color
        self.textcolor = textcolor

    async def get_payload(self):
        payload = {
            'widget_type': 'small_widget_text',
            'widget_id': self.widget_id,
            'data': {
                'position': self.position,
                'size': self.size,
                'text': self.text,
                'font_size': self.font_size,
                'color': self.color,
                'textcolor': self.textcolor,
            }
        }
        return payload

    def update(self, text=None, color=None, textcolor=None):
        self.text = text if text else self.text
        self.color = color if color else self.color
        self.textcolor = textcolor if textcolor else self.textcolor


# ----------------------------------------------------------------------------------------------------------------------
class SmallWidgetNumber(SmallWidget):

    def __init__(self, widget_id, value, precision, color="#101010", textcolor="#fff", size=None, position=None,
                 lockable=False, locked=False):
        super(SmallWidgetNumber, self).__init__(widget_id, position=position, size=size, lockable=lockable,
                                                locked=locked)

        if isinstance(color, list):
            color = rgb_to_hex(color)
        if isinstance(textcolor, list):
            textcolor = rgb_to_hex(textcolor)
        self.value = value
        self.precision = precision
        self.color = color
        self.textcolor = textcolor

    def update(self, value=None, color=None, textcolor=None):
        self.value = value if value else self.value
        self.color = color if color else self.color
        self.textcolor = textcolor if textcolor else self.textcolor

    async def get_payload(self):
        payload = {
            'widget_type': 'small_widget_number',
            'widget_id': self.widget_id,
            'data': {
                'position': self.position,
                'size': self.size,
                'value': self.value,
                'precision': self.precision,
                'color': self.color,
            }
        }
        return payload


# ----------------------------------------------------------------------------------------------------------------------
class SmallWidgetCircle(SmallWidget):
    def __init__(self, widget_id, circle_color, color="#101010", textcolor="#fff", size=None, position=None,
                 lockable=False, locked=False):
        super(SmallWidgetCircle, self).__init__(widget_id, position=position, size=size, lockable=lockable,
                                                locked=locked)

        if isinstance(color, list):
            color = rgb_to_hex(color)
        if isinstance(textcolor, list):
            textcolor = rgb_to_hex(textcolor)
        if isinstance(circle_color, list):
            circle_color = rgb_to_hex(circle_color)
        self.circle_color = circle_color
        self.color = color
        self.textcolor = textcolor

    async def get_payload(self):
        payload = {
            'widget_type': 'small_widget_circle',
            'widget_id': self.widget_id,
            'data': {
                'position': self.position,
                'size': self.size,
                'circle_color': self.circle_color,
                'color': self.color,
                'textcolor': self.textcolor,
            }
        }

    def update(self, circle_color=None, color=None, textcolor=None):
        if circle_color and isinstance(circle_color, list):
            circle_color = rgb_to_hex(circle_color)

        if color and isinstance(color, list):
            color = rgb_to_hex(color)

        if textcolor and isinstance(textcolor, list):
            textcolor = rgb_to_hex(textcolor)

        self.circle_color = circle_color if circle_color else self.circle_color
        self.color = color if color else self.color
        self.textcolor = textcolor if textcolor else self.textcolor


# ======================================================================================================================
class GridWidget(Widget):
    widgets: list[SmallWidget]

    def __init__(self, widget_id, title, grid_size: tuple, size=None, position=None, lockable=False, locked=False):
        super(GridWidget, self).__init__(widget_id, position=position, size=size, lockable=lockable, locked=locked)

        self.grid_size = grid_size

        self.widgets = []

    def add_widget(self, widget: SmallWidget, position: dict):
        ...  # Append position
        widget.grid_widget = self
        self.widgets.append(widget)

    def remove_widget(self, widget: SmallWidget):
        widget.grid_widget = None  # type: ignore
        self.widgets.remove(widget)

    async def get_payload(self):
        payload = {

        }


# ======================================================================================================================
class BackButton(Button):
    return_group: WidgetGroup

    def __init__(self, widget_id):
        name = 'Back'
        super(BackButton, self).__init__(widget_id, text='', icon='⬅️', color=[0.3, 0.3, 0.3], textcolor=[0, 0, 0],
                                         size=(1, 1),
                                         position={'page': 0, 'row': 1, 'column': 0})
        self.reserved = True
        self.return_group = None  # type: ignore

    async def on_pressed(self):
        if self.return_group is not None:
            return_data = {
                'event': 'switch_set',
                'path': self.return_group.get_path(),
                'payload': await self.return_group.root.get_group_payload(self.return_group.get_path(), 0),
            }
            return return_data
        return None


# ======================================================================================================================
class HomeButton(Button):

    def __init__(self, widget_id):
        name = 'Home'
        super(HomeButton, self).__init__(widget_id, name, icon='🏠', color=[0.3, 0.3, 0.3], textcolor=[0.9, 0.9, 0.9],
                                         size=(1, 1), position={'page': 0, 'row': 0, 'column': 0})
        self.reserved = True


# ======================================================================================================================
class FolderWidget(Button):
    callbacks: ButtonCallbacks
    target_group: WidgetGroup

    def __init__(self, widget_id, name, target_group, icon: str = '🗂', icon_position='center',
                 color: (list, str) = "#55FF55", textcolor: (list, str) = "#fff",
                 size=(1, 1), position=None, lockable=False, locked=False):
        super().__init__(widget_id=widget_id,
                         text=name,
                         icon=icon,
                         icon_position=icon_position,
                         position=position,
                         size=size,
                         lockable=lockable,
                         locked=locked)

        self.name = name
        self.target_group = target_group  # The target WidgetGroup that this folder represents.

        if color is None:
            color = [0.7, 0.7, 0.7]

        if isinstance(color, list):
            color = rgb_to_hex(color)

        if textcolor is None:
            textcolor = [0, 0, 0]

        if isinstance(textcolor, list):
            textcolor = rgb_to_hex(textcolor)

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
            'hidden': self.hidden,
            'icon': self.icon,
            'icon_position': self.icon_position,
        }

    async def on_pressed(self):
        if self.lockable and self.locked:
            return
        # return_data = {
        #     'event': 'switch_set',
        #     'path': self.target_group.get_path(),
        #     'payload': await self.target_group.root.get_group_payload(self.target_group.get_path(), 0),
        # }
        return_data = {
            'event': 'switch_set',
            'path': self.target_group.get_path(),
            # 'payload': await self.target_group.root.get_group_payload(self.target_group.get_path(), 0),
        }

        return return_data

    async def on_long_pressed(self):
        ...

    async def on_double_click(self):
        ...


# ======================================================================================================================
class ProxyFolderWidget(FolderWidget):
    def __init__(self, widget_id, name, target_group, icon: str = '🌐', icon_position='center',
                 color: (list, str) = "#55FF55", textcolor: (list, str) = "#fff",
                 size=(1, 1), position=None, lockable=False, locked=False):
        super(ProxyFolderWidget, self).__init__(widget_id, name, target_group, icon, icon_position,
                                                color, textcolor, size, position, lockable, locked)

        self.is_proxy = True

    async def get_payload(self):
        payload = await super(ProxyFolderWidget, self).get_payload()
        payload["is_proxy"] = True
        return payload


# ======================================================================================================================
class WidgetGroup:
    group_id: str
    parent_group: WidgetGroup
    child_groups: list[WidgetGroup]
    pages: int

    widgets: list[Widget]
    folder_widget: FolderWidget

    home_button: HomeButton
    back_button: BackButton

    app: ControlApp
    root: RootGroup

    is_root: bool = False

    def __init__(self, group_id: str, icon: str = '📂', icon_position: str = 'top', name: str = None, pages: int = 1,
                 color: (list, str) = None, textcolor: (list, str) = None, lockable: bool = False,
                 locked: bool = False):
        self.group_id = group_id.lower().replace(" ", "")

        if name is None:
            name = self.group_id

        self.name = name

        if self.group_id != group_id:
            logger.warning(f"WidgetGroup ID '{group_id}' has been changed to '{self.group_id}'.")

        assert pages >= 1
        self.pages = pages

        self.app = None  # type: ignore

        self.child_groups = []
        self.parent_group = None  # type: ignore
        self.is_root = False

        # Widgets Initialization
        self.widgets = []

        self.home_button = HomeButton(widget_id=f"home_{self.group_id}")
        self.addWidget(self.home_button)

        self.back_button = BackButton(widget_id=f"back_{self.group_id}")
        self.addWidget(self.back_button)

        self.folder_widget = FolderWidget(widget_id=f"{self.group_id}",
                                          name=self.name,
                                          icon=icon,
                                          icon_position=icon_position,
                                          target_group=self,
                                          color=color,
                                          textcolor=textcolor,
                                          lockable=lockable,
                                          locked=locked)

    # ------------------------------------------------------------------------------------------------------------------
    def get_path(self):
        if self.parent_group is None:
            return "/" + self.group_id
        else:
            return self.parent_group.get_path().rstrip("/") + "/" + self.group_id

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def uid(self):
        return f"{self.get_path()}"

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def parent_group(self):
        return self._parent_group

    # ------------------------------------------------------------------------------------------------------------------
    @parent_group.setter
    def parent_group(self, value):
        self._parent_group = value

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def root(self):
        current = self
        while current.is_root is False:
            current = current.parent_group
        return current

    # ------------------------------------------------------------------------------------------------------------------
    def addWidget(self, widget, position: dict = None):
        """
        Add a widget to the ButtonGroup.
        """

        if any(my_widget.widget_id == widget.widget_id for my_widget in self.widgets):
            logger.warning(f"Widget with ID '{widget.widget_id}' already exists in group '{self.group_id}'.Not added.")
            return

        widget.group = self
        if self.app is not None:
            widget.app = self.app

        self.widgets.append(widget)

        if position is not None:
            widget.position = position

        self._assign_position(widget)

        # Send update
        if self.app is not None:
            self.app.updateGroup(self.get_path())

        return widget

    # ------------------------------------------------------------------------------------------------------------------
    def addGroup(self, group: WidgetGroup, position: dict = None):

        if any(own_group.group_id == group.group_id for own_group in self.child_groups):
            logger.warning(f"Group with ID '{group.group_id}' already exists in group '{self.group_id}'.Not added.")
            return

        # Set the parent for the group being added.
        group.parent_group = self

        # Add the FolderWidget as a child into the parent's widget list.
        self.addWidget(group.folder_widget, position)
        self.child_groups.append(group)

        # Add myself as the return for the group's back button
        group.back_button.return_group = self

        if self.app is not None:
            self.app.assign_app_to_tree(group)

        # # TODO: Send Update
        # if self.app is not None:
        #     self.app.updateGroup(self.get_path())

    # ------------------------------------------------------------------------------------------------------------------
    def removeWidget(self, widget_id):
        """
        Remove a widget (not a group) by its ID.
        """
        if isinstance(widget_id, str):
            widget: Widget = self.getByPath(widget_id)

            if widget is None:
                logger.warning(f"Widget with ID '{widget_id}' not found in group '{self.group_id}'.")
                return
        elif isinstance(widget_id, Widget):
            widget = widget_id
        else:
            logger.warning("Remove Widget called with invalid argument.")
            return

        widget_group = widget.group

        if widget_group == self:
            self.widgets.remove(widget)
            widget.group = None  # type: ignore
            logger.debug(f"Removed widget {widget.uid} from group {self.uid}.")
        else:
            widget_group.widgets.remove(widget)

        if self.app is not None:
            self.app.updateGroup(self.get_path())

    # ------------------------------------------------------------------------------------------------------------------
    def removeGroup(self, group_id):
        """
        Remove a ButtonGroup (i.e. a folder) by its ID.
        """
        if isinstance(group_id, str):
            group: WidgetGroup = self.getGroupByPath(group_id)
            if group is None:
                logger.warning(f"WidgetGroup with ID '{group_id}' not found in group '{self.group_id}'.")
                return
        elif isinstance(group_id, WidgetGroup):
            group = group_id
        else:
            logger.warning("Remove Widget called with invalid argument.")
            return

        if group.parent_group == self:
            self.child_groups.remove(group)
            self.removeWidget(group.folder_widget.uid)
            group.parent_group = None
            logger.debug(f"Removed group '{group.group_id}' from group '{self.uid}'.")
        else:
            group.parent_group.remove_group(group)

        # if self.app is not None:
        #     self.app.updateGroup(self.get_path())

    # ------------------------------------------------------------------------------------------------------------------
    def getByPath(self, path: str):
        """
    # Resolves a widget or group by path relative to this group.
    # Accepts both absolute paths ("/root/folder/button"),
    # relative paths ("./folder/button"), or simple token paths ("folder/button").
    # Comparison is case- and space-insensitive.
    # Returns the widget/group if found, or None.
    #     """
        # Remove the app name first
        # print(path)
        # _, _, path = path.partition(":")
        # Choose the starting group:
        if path.startswith("/"):
            current = self.root  # Assumes get_root() is defined to retrieve the top-level group.
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
        # Only groups can have children, so for non-terminal tokens, enforce that constraint.
        for i, token in enumerate(tokens[1:], start=1):
            token_norm = normalize(token)
            found = None

            # Check both group children and widgets.
            # (Assuming that groups are stored in self.groups and widgets in self.widgets.)
            for child in current.child_groups + current.widgets:
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

    # ------------------------------------------------------------------------------------------------------------------
    def getWidgetByPath(self, path: str) -> Optional["Widget"]:
        """
        Resolve a widget by path relative to this group.
        Supports:
          - app:root/... (absolute, uses the full "app:root" first token)
          - /app:root/... (absolute)
          - ./foo/bar (relative)
          - foo/bar (relative)
        Comparison is case‑ and space‑insensitive.
        Returns the widget if found, else None.
        """
        # 1) Determine absolute vs. relative, pick a starting group and split into tokens
        absolute = False
        if path.startswith("/"):
            absolute = True
            current = self.root
            tokens = path.lstrip("/").split("/")
        elif path.startswith("./"):
            current = self
            tokens = path[2:].split("/")
        elif ":" in path and ("/" not in path or path.find(":") < path.find("/")):
            # e.g. "app:root/foo"
            absolute = True
            current = self.root
            tokens = path.split("/")
        else:
            current = self
            tokens = path.split("/")

        # 2) Normalizer
        def normalize(n: str) -> str:
            return n.strip().lower().replace(" ", "")

        # 3) If absolute, first token must match the root exactly, then drop it
        if absolute:
            if not tokens or normalize(tokens[0]) != normalize(self.root.group_id):
                return None
            tokens = tokens[1:]

        # 4) Nothing left ⇒ can't be a widget
        if not tokens:
            return None

        # 5) Traverse all but the last token through child_groups
        for seg in tokens[:-1]:
            seg_norm = normalize(seg)
            next_grp = next(
                (g for g in current.child_groups if normalize(g.group_id) == seg_norm),
                None
            )
            if next_grp is None:
                return None
            current = next_grp

        # 6) Final segment ⇒ look only in widgets
        last_norm = normalize(tokens[-1])
        return next(
            (w for w in current.widgets if normalize(w.widget_id) == last_norm),
            None
        )

    def getGroupByPath(self, path: str) -> Optional["WidgetGroup"]:
        """
        Resolve a group by path relative to this group.
        Supports:
          - app:root/...    (absolute, full "app:root")
          - /app:root/...   (absolute)
          - ./foo/bar       (relative)
          - foo/bar         (relative)
        Comparison is case‑ and space‑insensitive.
        Returns the group if found, else None.
        """
        # 1) Determine absolute vs. relative, pick starting group & split into tokens
        absolute = False
        if path.startswith("/"):
            absolute = True
            current = self.root
            tokens = path.lstrip("/").split("/")
        elif path.startswith("./"):
            current = self
            tokens = path[2:].split("/")
        elif ":" in path and ("/" not in path or path.find(":") < path.find("/")):
            # e.g. "app:root/foo"
            absolute = True
            current = self.root
            tokens = path.split("/")
        else:
            current = self
            tokens = path.split("/")

        # 2) Normalizer
        def normalize(n: str) -> str:
            return n.strip().lower().replace(" ", "")

        # 3) If absolute, first token must match the root exactly, then drop it
        if absolute:
            if not tokens or normalize(tokens[0]) != normalize(self.root.group_id):
                return None
            tokens = tokens[1:]

        # 4) Traverse every token through child_groups
        for seg in tokens:
            seg_norm = normalize(seg)
            next_grp = next(
                (g for g in current.child_groups if normalize(g.group_id) == seg_norm),
                None
            )
            if next_grp is None:
                return None
            current = next_grp

        return current

    # ------------------------------------------------------------------------------------------------------------------
    async def get_payload(self, page: int):
        """
        Return only the widgets on `page`, each with a dict-style position.
        """
        page = max(0, min(page, self.pages - 1))
        rows_per_page = GROUP_GRID_SIZE[0]
        widget_payloads = []

        for child in self.widgets:
            pos = child.position
            if not pos or pos["page"] != page:
                continue

            payload = await child.get_payload()
            payload["position"] = {
                "column": pos["column"],
                "row": pos["row"]
            }
            payload["grid_size"] = [child.size[0], child.size[1]]
            widget_payloads.append(payload)

        return {
            "set_name": self.uid,
            "group_type": "folder",
            "grid_size": [GROUP_GRID_SIZE[1], GRID_ROWS := rows_per_page],  # [cols, rows]
            "grid_items": widget_payloads,
            "path": self.get_path(),
            "current_page": page,
            "pages": self.pages,
        }

    # === PRIVATE METHODS ==============================================================================================
    def _compute_occupancy(self, exclude=None):
        """
        Build an occupancy grid for all pages×rows×cols,
        marking True where any non-placeholder widget sits.
        """
        grid_rows, grid_cols = GROUP_GRID_SIZE
        total_rows = self.pages * grid_rows

        # flat 2D array: [0..total_rows-1][0..grid_cols-1]
        occupancy = [[False] * grid_cols for _ in range(total_rows)]

        for child in self.widgets:
            if child is exclude or getattr(child, "is_placeholder", False):
                continue
            pos = child.position
            if not pos:
                continue

            p = pos["page"] or 0
            r = pos["row"]
            c = pos["column"]
            w, h = child.size

            base_row = p * grid_rows + r
            for dr in range(h):
                for dc in range(w):
                    occupancy[base_row + dr][c + dc] = True

        return occupancy

    # ------------------------------------------------------------------------------------------------------------------
    def _assign_position(self, widget: Widget):
        """
        New position assignment:
          - If user provided page,row,column all three ⇒ strict validate & set.
          - Otherwise scan only allowed pages/rows/columns, honoring any partial constraints.
        """
        w, h = widget.size or (1, 1)
        grid_rows, grid_cols = GROUP_GRID_SIZE
        reserved = getattr(widget, "reserved", False)

        # extract any user constraints
        pos = widget.position or {}
        fixed_page = pos.get("page")
        fixed_row = pos.get("row")
        fixed_column = pos.get("column")

        # Manual placement if all three are given:
        if fixed_page is not None and fixed_row is not None and fixed_column is not None:
            # bounds checks
            if not (0 <= fixed_page < self.pages):
                raise ValueError(f"Page {fixed_page} out of range [0..{self.pages - 1}].")
            if not (0 <= fixed_row <= grid_rows - h):
                raise ValueError(f"Row {fixed_row} out of range for height {h}.")
            if not (0 <= fixed_column <= grid_cols - w):
                raise ValueError(f"Column {fixed_column} out of range for width {w}.")
            # reserved‑column enforcement
            if (not reserved
                    and fixed_column < 1
                    and not (ALLOW_FIRST_COLUMN_ON_SUBSEQUENT_PAGES and fixed_page > 0)
            ):
                raise ValueError(f"Widget {widget.widget_id} cannot sit in column 0 on page {fixed_page}.")
            # check no overlap
            occ = self._compute_occupancy(exclude=widget)
            base = fixed_page * grid_rows + fixed_row
            for dr in range(h):
                for dc in range(w):
                    if occ[base + dr][fixed_column + dc]:
                        raise ValueError(f"Overlap at ({fixed_column},{fixed_row}) on page {fixed_page}.")
            widget.position = {"page": fixed_page,
                               "row": fixed_row,
                               "column": fixed_column}
            return

        # Auto‑placement with partial constraints:
        occ = self._compute_occupancy(exclude=widget)
        pages = [fixed_page] if fixed_page is not None else range(self.pages)
        for p in pages:
            page_offset = p * grid_rows
            min_col = 0 if (reserved or (ALLOW_FIRST_COLUMN_ON_SUBSEQUENT_PAGES and p > 0)) else 1

            rows = ([fixed_row] if fixed_row is not None else range(0, grid_rows - h + 1))
            for r in rows:
                if r + h > grid_rows:
                    continue
                cols = ([fixed_column] if fixed_column is not None else range(min_col, grid_cols - w + 1))
                for c in cols:
                    # no overlap?
                    base = page_offset + r
                    conflict = any(
                        occ[base + dr][c + dc]
                        for dr in range(h) for dc in range(w)
                    )
                    if not conflict:
                        widget.position = {"page": p, "row": r, "column": c}
                        return

        raise ValueError(f"No space to place widget {widget.widget_id} with constraints {pos}")


# ======================================================================================================================
class RootGroup(WidgetGroup):
    is_root = True

    # ==================================================================================================================
    def __init__(self, group_id: str, pages: int = 1, color=None, textcolor=None):
        super(RootGroup, self).__init__(group_id, pages=pages, color=color, textcolor=textcolor)
        self.is_root = True

        self.back_button.hidden = True

    @property
    def app(self):
        return self._app

    @app.setter
    def app(self, value):
        self._app = value
        if value is not None:
            self.group_id = f"{self.app.app_id}:{self.group_id}"
            self.back_button.widget_id = f"back_{self.group_id}"
            self.home_button.widget_id = f"home_{self.group_id}"

    # ------------------------------------------------------------------------------------------------------------------
    async def handle_widget_message(self, data):

        widget_id: str = data.get('id', None)

        if widget_id is None:
            logger.error(f"No widget id in message: {data}")
            return None

        # Check if the widget exists
        widget = self.getWidgetByPath(widget_id)

        if widget is None:
            is_local, child_app, child_app_path = self.check_path(widget_id)
            if not is_local:
                # logger.info(f"Widget {widget_id} is not local to this app: {data}")
                return await self.app.handle_remote_widget_message(child_app, child_app_path, data)
            else:
                logger.warning(f"Widget {widget_id} not found")
                return None

        logger.debug(f"Handling widget message for {widget_id} of type {type(widget)}: {data}")

        # I have to update this: I already got the widget, I don't have to look for it!
        if data.get("event_type") == "button_click":
            if hasattr(widget, "on_pressed"):
                return await widget.on_pressed()
            return None

        elif data.get("event_type") == "multi_state_button_click":
            if isinstance(widget, MultiStateButton):
                return await widget.on_pressed()
            return None

        elif data.get("event_type") == "multi_state_button_double_click":
            if hasattr(widget, "on_double_click"):
                return await widget.on_double_click()
            return None

        elif data.get("event_type") == "multi_state_button_long_click":
            if hasattr(widget, "on_long_pressed"):
                return await widget.on_long_pressed()
            return None

        elif data.get("event_type") == "button_double_click":
            if hasattr(widget, "on_double_click"):
                return await widget.on_double_click()
            return None

        elif data.get("event_type") == "button_long_click":
            if hasattr(widget, "on_long_pressed"):
                return await widget.on_long_pressed()
            return None

        elif data.get("event_type") == "multi_select_change":
            new_value = data.get("value", None)
            if hasattr(widget, "on_value_change"):
                return await widget.on_value_change(new_value)
            return None

        elif data.get("event_type") == "slider_change":
            new_value = data.get("value")

            if hasattr(widget, "on_value_changed"):
                return await widget.on_value_changed(new_value)
            return None

        elif data.get("event_type") == "editable_value_change":
            new_value = data.get("value", "")
            if hasattr(widget, "on_value_changed"):
                return await widget.on_value_changed(new_value)
            return None
        # New handling for JoystickWidget events
        elif data.get("event_type") == "joystick_change":
            new_x = data.get("x")
            new_y = data.get("y")
            if hasattr(widget, "on_value_changed"):
                return await widget.on_value_changed(new_x, new_y)
            return None
        elif data.get("event_type") == "update_digitalnumber":
            # This is handled on the client side; no server action needed here.
            return None

        elif data.get("event_type") == "rotary_dial_change":
            new_value = data.get("value", None)
            if new_value is None:
                return None
            if hasattr(widget, "on_value_changed"):
                return await widget.on_value_changed(float(new_value))
            return None


        # New handling for SplitButton events
        elif data.get("event_type") == "split_button_click":
            part = data.get("part")
            if hasattr(widget, "on_part_pressed"):
                return await widget.on_part_pressed(part)
            return None

        elif data.get("event_type") == "split_button_double_click":
            part = data.get("part")
            if hasattr(widget, "on_part_double_click"):
                return await widget.on_part_double_click(part)
            return None

        elif data.get("event_type") == "split_button_long_click":
            part = data.get("part")
            if hasattr(widget, "on_part_long_pressed"):
                return await widget.on_part_long_pressed(part)
            return None

        # New: Handle long press events from sliders, joysticks, and multi_select
        elif data.get("event_type") == "slider_long_click":
            logger.info(f"Slider {data.get('id')} long pressed.")
            return None
        elif data.get("event_type") == "joystick_long_click":
            logger.info(f"Joystick {data.get('id')} long pressed.")
            return None
        elif data.get("event_type") == "multi_select_long_click":
            logger.info(f"MultiSelect {data.get('id')} long pressed.")
            return None

        # NEW: Handle incoming popup trigger if needed.
        elif data.get("event_type") == "popup":
            # Not expected from the client.
            return None
        return None

    # ------------------------------------------------------------------------------------------------------------------
    async def get_group_payload(self, group: str, page: int):
        # Check if the group is local
        is_local, child_app, child_app_path = self.check_path(group)

        if not is_local:
            logger.debug(f"Group {group} is not local to this app.")
            logger.debug(f"Getting group payload from remote app {child_app} at path {child_app_path}")
            # return
            return await self.app.get_remote_payload(child_app, child_app_path, page)
        else:
            group = self.getGroupByPath(group)
            if group is None:
                print(f"Group {group} not found.")
                return None

            payload = await group.get_payload(page)

        return payload

    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def check_path(path):
        # Split path by '/' and filter out empty parts
        parts = [p for p in path.split('/') if p]

        # Identify all root folders
        root_folders = [p for p in parts if ':' in p]

        # A path is local if there is only one or no root folder
        is_local = len([p for p in parts if ':' in p and re.match(r'.+:.+', p)]) <= 1

        # Find the first root folder that is NOT the first in the path
        first_root_index = next(
            (i for i, p in enumerate(parts) if ':' in p and re.match(r'.+:.+', p) and i != 0),
            None
        )

        if first_root_index is not None:
            child_app_folder = parts[first_root_index]
            child_app_path = '/' + '/'.join(parts[first_root_index:])
        else:
            child_app_folder = None
            child_app_path = None

        return is_local, child_app_folder, child_app_path


# ======================================================================================================================
class ProxyRootGroup(RootGroup):
    child_app: ControlAppChild

    def __init__(self, child_app, group_id: str, pages: int = 1,
                 color: (list, str) = None, textcolor: (list, str) = None):
        super(ProxyRootGroup, self).__init__(group_id, pages, color, textcolor)

        self.child_app = child_app

        self.folder_widget = ProxyFolderWidget(
            widget_id=f"{self.group_id}",
            name=group_id,
            target_group=self,
            color=color,
            textcolor=textcolor,
        )

        # self.back_button.hidden = False

        logger.debug(f"ProxyRootGroup: {self.group_id} created. Path {self.get_path()}")

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def app(self):
        return self._app

    # ------------------------------------------------------------------------------------------------------------------
    @app.setter
    def app(self, value):
        self._app = value


# ======================================================================================================================
class Frontend:
    websocket: web.WebSocketResponse
    current_path: str
    current_page: int
    root_group: RootGroup

    def __init__(self, websocket, root_group: RootGroup):

        self.websocket = websocket
        self.root_group = root_group

        self.current_path = None  # type: ignore
        self.current_page = 0

        self._poller_task: asyncio.Task | None = None

    # ------------------------------------------------------------------------------------------------------------------
    async def init(self):
        await self.set_current_path(path=self.root_group.get_path(),
                                    page=0,
                                    payload=await self.root_group.get_group_payload(self.root_group.group_id, 0))

        self.root_group.app.updateStatusBar()

    # ------------------------------------------------------------------------------------------------------------------
    async def close(self):
        # called when this Frontend is being shut down
        if self._poller_task:
            self._poller_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._poller_task
            self._poller_task = None

        # then you can close the websocket (or whatever else you need)
        await self.websocket.close()
        logger.debug("Frontend closed.")

    # ------------------------------------------------------------------------------------------------------------------
    async def send_json(self, message):
        await self.websocket.send_json(message)

    # ------------------------------------------------------------------------------------------------------------------
    async def handle_message_from_web(self, data):
        match data.get('type', None):
            case 'widget':
                asyncio.create_task(self.handle_widget_message(data))
            case 'navigation':
                asyncio.create_task(self.handle_navigation_message_from_web(data))
            case 'special':
                await self.root_group.app.handle_special_message(data)
            case 'command':
                logger.debug(f"Received command: {data}")
            case _:
                logger.warning(f"Unknown message type: {data}")

    # ------------------------------------------------------------------------------------------------------------------
    async def set_current_path(self, path, payload, page):
        self.current_path = path
        self.current_page = page
        payload['type'] = 'switch_set'
        await self.send_json(payload)

    # ------------------------------------------------------------------------------------------------------------------
    async def switch_set(self, path, page):
        payload = await self.root_group.get_group_payload(path, page)
        if payload is None:
            return
        logger.debug(f"Switching to set {path} on page {page}. Got Payload: {payload}")
        if payload is not None:
            await self.set_current_path(path, payload, page)

    # ------------------------------------------------------------------------------------------------------------------
    async def handle_widget_message(self, data):
        return_value = await self.root_group.handle_widget_message(data)

        if isinstance(return_value, dict):
            event = return_value.get('event', None)

            if event == 'switch_set':
                path = return_value.get('path', None)
                page = return_value.get('page', 0)
                logger.debug(f"Switch Set return: {path}:{page}")
                asyncio.create_task(self.switch_set(path, page))

    # ------------------------------------------------------------------------------------------------------------------
    async def handle_navigation_message_from_web(self, data):
        logger.debug(f"Got a navigation message from the web: {data}")
        event_type = data.get("event_type", None)

        if event_type is None:
            return

        match event_type:
            case "page_change":
                # New: Handle page change requests.
                if "page" in data:
                    new_page = int(data.get("page"))
                else:
                    direction = data.get("direction")

                    if direction == "down":
                        new_page = self.current_page + 1
                    elif direction == "up":
                        new_page = self.current_page - 1
                    else:
                        return

                payload = await self.root_group.get_group_payload(self.current_path, new_page)
                new_page = payload['current_page']

                if new_page != self.current_page:
                    await self.set_current_path(self.current_path, payload, new_page)  # type: ignore

            case _:
                logger.warning(f"Unknown navigation event type: {event_type}")

    # # ------------------------------------------------------------------------------------------------------------------
    # async def handle_special_message(self, data):
    #     print("DO I HANDLE THE SPECIAL MESSAGE?")

    # ------------------------------------------------------------------------------------------------------------------
    async def update_group_event(self, path):
        if path == self.current_path:
            asyncio.create_task(self.switch_set(self.current_path, self.current_page))

    # ------------------------------------------------------------------------------------------------------------------
    async def path_removal_event(self, path):
        if is_subpath(path, self.current_path):
            await self.switch_set(path=self.root_group.get_path(), page=0)


# ======================================================================================================================
class ControlAppChild:
    child_app_id: str
    address: str
    port: int

    folder_path: str

    def __init__(self, child_app_id, address, port, root_folder_id, root_folder_pages, websocket, app: ControlApp):
        self.child_app_id = child_app_id
        self.address = address
        self.port = port
        self.websocket = websocket

        self.app = app

        self.root_folder_id = root_folder_id

        self.pending_requests = {}

        self.root_group = ProxyRootGroup(self, self.root_folder_id, pages=root_folder_pages)

        # TODO: For now, put the group onto the root of the app

        self.app.root_group.addGroup(self.root_group)

    # ------------------------------------------------------------------------------------------------------------------
    async def get_folder_payload(self, folder_path, page=0):

        # Generate a unique correlation ID
        request_id = str(uuid.uuid4())

        # Create a Future to wait for the response
        future = self.app.event_loop.create_future()
        self.pending_requests[request_id] = future

        # Prepare the message with the folder path and the unique request ID
        message = {
            'type': 'request',
            'request_type': 'get_folder_payload',
            'folder_path': folder_path,
            'page': page,
            'request_id': request_id
        }

        logger.debug(f"Child App {self.child_app_id}: sending payload request for {folder_path}...")
        # Send the request message to the child via the WebSocket connection
        await self.websocket.send_json(message)

        try:
            # Wait for the response to arrive with a timeout (e.g., 10 seconds)
            payload = await asyncio.wait_for(future, timeout=5)

            if payload is not None:
                payload = self._modify_payload_ids(payload)

                # Unhide the back button for the root folder
                if payload['path'] == self.root_group.get_path():
                    for item in payload['grid_items']:
                        if item['id'] == self.root_group.back_button.uid:
                            item['hidden'] = False
                            break

            logger.debug(f"Child App {self.child_app_id}: received payload from the server: {payload}")
            return payload
        except asyncio.TimeoutError:
            logger.warning(f"Child App {self.child_app_id}: Timeout error for payload on {folder_path}.")
            return None
        finally:
            # Clean up the pending request so we don't leak memory
            self.pending_requests.pop(request_id, None)

    # ------------------------------------------------------------------------------------------------------------------
    def _modify_payload_ids(self, payload):
        payload['set_name'] = prepend_parent_path(payload['set_name'], self.root_group.get_path())
        payload['path'] = prepend_parent_path(payload['path'], self.root_group.get_path())
        for item in payload['grid_items']:
            item['id'] = prepend_parent_path(item['id'], self.root_group.get_path())
        return payload

    # ------------------------------------------------------------------------------------------------------------------
    async def handle_message(self, msg):
        """
        This method should be called in your WebSocket message handler whenever a message
        is received from the child. It inspects the message for a 'request_id' and sets the result
        for the corresponding pending request.
        """
        try:
            message_data = json.loads(msg)
        except Exception as e:
            # Handle JSON decode error here if needed
            return None

        type = message_data.get('type', None)
        # print(f"Got message from child of type {type}")
        match type:
            case 'response':
                # Check if the message is a reply with a request_id that matches one of our pending requests
                request_id = message_data.get("request_id")

                if request_id and request_id in self.pending_requests:
                    # Check if the data is for a folder, then modify the paths
                    data = message_data.get("data", None)
                    if data is not None:
                        if data.get('event', None) is not None and data['event'] == 'switch_set':
                            data['path'] = prepend_parent_path(data['path'], self.root_group.get_path())

                    future = self.pending_requests[request_id]
                    if not future.done():
                        # You can extract the actual payload from the response as needed (e.g., data.get("payload"))
                        future.set_result(message_data.get("data"))
                        return None
                    return None
                else:
                    # Process message that is not responses to our requests
                    return None

            case 'update_widget':
                widget_data = message_data.get("data", None)
                if widget_data is not None:
                    widget_id_in_parent = prepend_parent_path(widget_data['id'], self.root_group.get_path())
                    widget_data['id'] = widget_id_in_parent
                    await self.app.update_widget(widget_data)
                    return None
                return None

            case 'update_group':
                raise NotImplementedError("I have to implement this.")

            case _:
                logger.error(f"Unknown message type: {type}")
                return None

    # ------------------------------------------------------------------------------------------------------------------
    async def handle_widget_message(self, data):

        request_answer = False

        if data.get('event_type', None) == 'button_click':
            request_answer = True

        if not request_answer:
            await self.websocket.send_json(data)
            return None

        # Generate a unique correlation ID
        request_id = str(uuid.uuid4())

        # Create a Future to wait for the response
        future = self.app.event_loop.create_future()
        self.pending_requests[request_id] = future

        # Prepare the message with the folder path and the unique request ID
        message = {
            'type': 'request',
            'request_type': 'widget',
            'data': data,
            'request_id': request_id
        }

        await self.websocket.send_json(message)
        try:
            # Wait for the response to arrive with a timeout (e.g., 10 seconds)
            return_data = await asyncio.wait_for(future, timeout=5)
            logger.debug(f"Child App {self.child_app_id}: received response payload from the server: {return_data}")
            return return_data
        except asyncio.TimeoutError:
            logger.warning(f"Child App {self.child_app_id}: Timeout error")
            return None
        finally:
            # Clean up the pending request so we don't leak memory
            self.pending_requests.pop(request_id, None)
            # return None

    # ------------------------------------------------------------------------------------------------------------------
    def close(self):
        self.app.root_group.removeGroup(self.root_group)
        pass


# ======================================================================================================================
# ======================================================================================================================
class StatusBarWidget(ABC):
    size: (int, int)
    position: dict  # {'row': int, 'col': int}
    widget_id: str
    visible: bool
    status_bar: StatusBar
    widget_type: str

    def __init__(self, widget_id: str, size: tuple, position: dict, visible: bool = True):
        self.widget_id = widget_id
        self.size = size
        self.position = position
        self.visible = visible
        self.status_bar = None

    @abstractmethod
    async def get_payload(self) -> dict:
        ...

    @abstractmethod
    def set_visible(self, visible: bool):
        ...


# ======================================================================================================================
class ImageStatusBarWidget(StatusBarWidget):
    image_path: str
    widget_type = "image"

    def __init__(self, widget_id: str, image_path: str, size: tuple, position: dict):
        super().__init__(widget_id, size, position)
        self.image_path = image_path

    def update(self, image_path: str):
        self.image_path = image_path
        self.status_bar.updateWidget(self)

    def set_visible(self, visible: bool):
        if visible != self.visible:
            self.visible = visible
            self.status_bar.updateWidget(self)

    async def get_payload(self):
        payload = {
            'widget_type': 'image',
            'widget_id': self.widget_id,
            'data': {
                'size': self.size,
                'position': self.position,
                'image_path': self.image_path,
                'visible': self.visible
            }
        }
        return payload


class ConnectionStrengthStatusBarWidget(StatusBarWidget):
    bar_color: str
    strength: str  # 'low', 'medium', 'high'
    widget_type = "connection"

    def __init__(self, widget_id, bar_color: str | list, strength: str, position: dict = None, size: tuple = (2, 1)):
        super(ConnectionStrengthStatusBarWidget, self).__init__(widget_id, size, position)
        if isinstance(bar_color, list):
            bar_color = rgb_to_hex(bar_color)

        assert strength in ['low', 'medium', 'high']

        self.bar_color = bar_color
        self.strength = strength

    def update(self, strength: str):
        if strength not in ['low', 'medium', 'high']:
            logger.warning(f"Invalid strength value: {strength}")
            return

        self.strength = strength

        self.status_bar.updateWidget(self)

    async def get_payload(self):
        payload = {
            'widget_type': 'connection',
            'widget_id': self.widget_id,
            'data': {
                'position': self.position,
                'size': self.size,
                'strength': self.strength,
                'bar_color': self.bar_color,
                'visible': self.visible
            }
        }
        return payload

    def set_visible(self, visible: bool):
        if visible != self.visible:
            self.visible = visible
            self.status_bar.updateWidget(self)


class InternetStatusBarWidget(StatusBarWidget):
    has_internet: bool
    widget_type = "internet"

    def __init__(self, widget_id, has_internet: bool, size: tuple = (2, 1), position: dict = None):
        super(InternetStatusBarWidget, self).__init__(widget_id, size, position)
        self.has_internet = has_internet

    def update(self, has_internet: bool):
        self.has_internet = has_internet
        self.status_bar.updateWidget(self)

    async def get_payload(self) -> dict:
        payload = {
            'widget_type': 'internet',
            'widget_id': self.widget_id,
            'data': {
                'position': self.position,
                'size': self.size,
                'visible': self.visible,
                'has_internet': self.has_internet
            }
        }
        return payload

    def set_visible(self, visible: bool):
        if visible != self.visible:
            self.visible = visible
            self.status_bar.updateWidget(self)


class JoystickStatusBarWidget(StatusBarWidget):
    connected: bool
    widget_type = "joystick"

    def __init__(self, widget_id, connected: bool, size: tuple = (1, 1), position: dict = None):
        super(JoystickStatusBarWidget, self).__init__(widget_id, size, position)
        self.connected = connected

    def update(self, connected: bool):
        self.connected = connected
        self.status_bar.updateWidget(self)

    async def get_payload(self) -> dict:
        payload = {
            'widget_type': 'joystick',
            'widget_id': self.widget_id,
            'data': {
                'position': self.position,
                'size': self.size,
                'visible': self.visible,
                'connected': self.connected
            }
        }
        return payload

    def set_visible(self, visible: bool):
        if visible != self.visible:
            self.visible = visible
            self.status_bar.updateWidget(self)


class BatteryLevelStatusBarWidget(StatusBarWidget):
    voltage: float
    percentage: float
    thresholds: list  # [critical_percentage, low_percentage, medium_percentage, high_percentage]
    voltage_precision: int = 1
    show_voltage: bool = True
    widget_type = "battery"

    def __init__(self, widget_id,
                 voltage: float = 0,
                 percentage: float = 0,
                 thresholds: list = None,
                 voltage_precision: int = 1,
                 show_voltage: bool = True,
                 size: tuple = (2, 1),
                 position: dict = None):
        super(BatteryLevelStatusBarWidget, self).__init__(widget_id, size, position)
        self.voltage = voltage
        self.percentage = percentage

        if thresholds is None:
            thresholds = [10, 25, 50, 90]

        self.thresholds = thresholds
        self.voltage_precision = voltage_precision
        self.show_voltage = show_voltage

    def update(self, voltage: float, percentage: float):
        self.voltage = voltage
        self.percentage = percentage
        self.status_bar.updateWidget(self)

    async def get_payload(self):
        payload = {
            'widget_type': 'battery',
            'widget_id': self.widget_id,
            'data': {
                'position': self.position,
                'size': self.size,
                'show_voltage': self.show_voltage,
                'voltage': round(self.voltage, self.voltage_precision),
                'percentage': round(self.percentage, 1),
                'thresholds': self.thresholds,
                'visible': self.visible
            }
        }
        return payload

    def set_visible(self, visible: bool):
        if visible != self.visible:
            self.visible = visible
            self.status_bar.updateWidget(self)


class TextStatusBarWidget(StatusBarWidget):
    prefix: str
    text: str
    textcolor: str
    alignment: str  # 'left', 'right', 'center'
    font_size: str  # 'normal', 'big'
    widget_type = "text"

    def __init__(self, widget_id,
                 prefix: str = '',
                 text: str = '',
                 textcolor: (str, list) = '#FFFFFF',
                 color=None,
                 alignment: str = 'center',
                 font_size: str = 'normal',
                 bold: bool = False,
                 bold_prefix: bool = False,
                 italic: bool = False,
                 size: tuple = (2, 1),
                 position: dict = None):
        super(TextStatusBarWidget, self).__init__(widget_id, size, position)

        assert font_size in ['normal', 'big', 'small']

        if isinstance(textcolor, list):
            textcolor = rgb_to_hex(textcolor)

        if isinstance(color, list):
            color = rgb_to_hex(color)

        self.prefix = prefix
        self.text = text
        self.textcolor = textcolor
        self.color = color
        self.alignment = alignment
        self.font_size = font_size
        self.bold = bold
        self.bold_prefix = bold_prefix
        self.italic = italic

    def update(self, text: str):
        self.text = text
        self.status_bar.updateWidget(self)

    async def get_payload(self) -> dict:
        payload = {
            'widget_type': 'text',
            'widget_id': self.widget_id,
            'data': {
                'position': self.position,
                'size': self.size,
                'alignment': self.alignment,
                'font_size': self.font_size,
                'visible': self.visible,
                'text': f"<b>{self.prefix}</b> {self.text}" if self.bold_prefix else self.prefix + self.text,
                'textcolor': self.textcolor,
                'bold': self.bold,
                'italic': self.italic,
                'color': self.color
            }
        }
        return payload

    def set_visible(self, visible: bool):
        if visible != self.visible:
            self.visible = visible
            self.status_bar.updateWidget(self)


class CircleStatusBarWidget(StatusBarWidget):
    color: str
    widget_type = "circle"

    def __init__(self, widget_id, color: str | list, size: tuple = (2, 1), position: dict = None):
        super(CircleStatusBarWidget, self).__init__(widget_id, size, position)

        if isinstance(color, list):
            color = rgb_to_hex(color)

        self.color = color

    def update(self, color: str):
        if isinstance(color, list):
            color = rgb_to_hex(color)
        self.color = color
        self.status_bar.updateWidget(self)

    async def get_payload(self) -> dict:
        payload = {
            'widget_type': 'circle',
            'widget_id': self.widget_id,
            'data': {
                'position': self.position,
                'size': self.size,
                'color': self.color,
                'visible': self.visible
            }
        }
        return payload

    def set_visible(self, visible: bool):
        if visible != self.visible:
            self.visible = visible
            self.status_bar.updateWidget(self)


# ======================================================================================================================

STATUS_BAR_GRID_SIZE = (20, 2)  # (columns, rows)


class StatusBar:
    widgets: list[StatusBarWidget]
    app: ControlApp

    def __init__(self, app: ControlApp):
        self.app = app
        self.widgets = []

    def addWidget(self, widget: StatusBarWidget, position=None):
        """
        Add a widget to the status bar, erroring if it overlaps any existing one.
        """
        # Allow caller to override position
        if position is not None:
            widget.position = position

        # Ensure we have a position
        if widget.position is None:
            raise ValueError("Position must be specified.")

        # Extract new widget’s bounds
        new_c = widget.position['column']
        new_r = widget.position['row']
        new_w, new_h = widget.size

        # Check against all already-added widgets
        for existing in self.widgets:
            ex_c = existing.position['column']
            ex_r = existing.position['row']
            ex_w, ex_h = existing.size

            # If rectangles intersect on both axes → overlap
            if not (
                    new_c + new_w <= ex_c or  # new is entirely left of existing
                    ex_c + ex_w <= new_c or  # new is entirely right of existing
                    new_r + new_h <= ex_r or  # new is entirely above existing
                    ex_r + ex_h <= new_r  # new is entirely below existing
            ):
                raise ValueError(
                    f"Cannot add status-bar widget '{widget.widget_id}': "
                    f"overlaps with '{existing.widget_id}'"
                )

        # All good—add it
        self.widgets.append(widget)
        widget.status_bar = self

        # Trigger a redraw
        if self.app is not None:
            self.app.updateStatusBar()

    async def get_payload(self):
        widget_data = []

        for widget in self.widgets:
            widget_data.append(await widget.get_payload())

        return widget_data

    def updateWidget(self, widget: StatusBarWidget):
        if self.app is not None:
            self.app.updateStatusBarWidget(widget)


# ======================================================================================================================

class ControlApp:
    root_group: RootGroup
    children: dict[str, ControlAppChild]
    frontends: list[Frontend]

    status_bar: StatusBar

    _exit: bool

    def __init__(self, app_id: str, port=80, mdns_name: str = 'bilbolab', parent_address: str = None,
                 parent_port: int = 80):

        self.static_path = None
        self.running = False
        self.app_id = app_id

        self.status_bar = StatusBar(self)

        # Network
        self.address = None
        self.port = port
        self.mdns_name = mdns_name

        self.clients = set()  # TODO: Do I need this?
        self.webapp_clients = set()

        self.frontends: list[Frontend] = []

        # If the App is a child app
        self.parent_address = parent_address
        self.parent_port = parent_port
        self.parent_websocket = None

        # If the app is a parent
        self.children = {}
        self.active_child = None

        # Web Application
        self.app = web.Application()
        self.runner = None  # Will hold our AppRunner.

        # Asyncio
        self.event_loop = None  # Will hold our event loop.

        # Group Handling
        # self.current_group = None
        self.root_group = None  # type: ignore

        self._popup_callbacks: dict[str, Callable[[str], None]] = {}

        self._exit = False

    # ------------------------------------------------------------------------------------------------------------------
    def init(self, root_group: RootGroup):
        self.root_group = root_group
        # self.current_group = root_group
        self.assign_app_to_tree(root_group)
        self.setup_routes()

    # ------------------------------------------------------------------------------------------------------------------
    def setup_routes(self):
        self.static_path = os.path.join(os.path.dirname(__file__), "static")
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/ws', self.websocket_handler)
        self.app.router.add_static('/', self.static_path, name='static')
        self.app.router.add_get('/info', self.info_handler)

    # ------------------------------------------------------------------------------------------------------------------
    def run(self):
        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)

        self.runner = web.AppRunner(self.app)
        self.event_loop.run_until_complete(self.runner.setup())

        ip = getValidHostIP()
        if ip is None:
            ip = '127.0.0.1'

        self.address = ip
        site = web.TCPSite(self.runner, host="0.0.0.0", port=self.port)
        self.event_loop.run_until_complete(site.start())

        self.running = True
        if self.parent_address:
            self.event_loop.create_task(self._connectToParent(self.parent_address, self.parent_port))

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
            self.event_loop.run_forever()
        finally:
            self.event_loop.run_until_complete(self.runner.cleanup())
            if zeroconf_instance and service_info:
                zeroconf_instance.unregister_service(service_info)
                zeroconf_instance.close()
            logger.info("Closing")
            self._exit = True

    # ------------------------------------------------------------------------------------------------------------------
    def run_in_thread(self):
        if self.root_group is None:
            raise ValueError("App has not been initialized.")

        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread

    # ------------------------------------------------------------------------------------------------------------------
    def close(self):
        if self.event_loop and self.event_loop.is_running():
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
            logger.info("Server close requested.")
            self._exit = True

    # ------------------------------------------------------------------------------------------------------------------
    async def info_handler(self, request: Request):
        """
        Returns some JSON info indicating that we're alive and well,
        plus any other metadata you want to expose.
        """
        logger.debug(f"Some is requesting info: {request.remote}")
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
    def log(self, text, color=None):

        if color is None:
            color = [1, 0, 0]

        if isinstance(color, (list, tuple)):
            color = rgb_to_hex(color)

        data = {
            'type': 'log',
            'message': text,
            'color': color
        }
        for frontend in self.frontends:
            asyncio.create_task(frontend.send_json(data))

    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    async def check_target_app_is_up(target_host: str, port=None):
        """
        Async version that will correctly handle app1.local (mDNS) as well as IPs/real names.
        """
        resolver = MDNSResolver()
        connector = TCPConnector(resolver=resolver, ssl=False)

        async with ClientSession(connector=connector) as session:
            try:
                addresses = await resolver.resolve(target_host)
                if not addresses:
                    return
                address = addresses[0]
                if address['port'] == 0:
                    return None
                else:
                    ...
                logger.debug(f"Target host {target_host} resolved to {address['host']}:{address['port']}")

            except Exception as e:
                # logger.warning(f"Target host {target_host} could not be resolved: {e}")
                return None

            # Check if the app responds
            try:
                resp = await session.get(f"http://{target_host}/info", timeout=2)
                if resp.status == 200:
                    data = await resp.json()
                    logger.debug(f"Got info from {target_host}: {data}")
                await resp.release()

                return data

            except Exception as e:
                logger.error(f"Could not connect to {target_host} (status: {resp.status})")
                return None

    # ------------------------------------------------------------------------------------------------------------------
    def assign_app_to_tree(self, group):
        group.app = self
        for child in group.widgets + group.child_groups:
            if isinstance(child, WidgetGroup):
                self.assign_app_to_tree(child)
            else:
                child.app = self

    # ------------------------------------------------------------------------------------------------------------------
    async def index(self, request):
        return web.FileResponse(f"{self.static_path}/index.html")

    # ------------------------------------------------------------------------------------------------------------------
    async def websocket_handler(self, request):
        ws = web.WebSocketResponse(heartbeat=10)
        await ws.prepare(request)
        self.clients.add(ws)

        client_type = None
        client_id = None
        frontend = None

        async for msg in ws:
            msg: WSMessage

            match msg.type:
                case web.WSMsgType.TEXT:
                    data = None
                    try:
                        data = json.loads(msg.data)
                        msg_type = data.get('type', None)

                        if client_type is None and msg_type == 'handshake':
                            # Register the client
                            client_type = data.get('client', None)
                            if client_type == 'web':
                                client_id = 'web'

                                # self.webapp_clients.add(ws)
                                frontend = Frontend(websocket=ws, root_group=self.root_group)
                                await frontend.init()
                                self.frontends.append(frontend)
                                logger.debug(f"Added Frontend")

                            elif client_type == 'control_app':
                                client_id = data.get('id', None)
                                asyncio.create_task(self._registerChildApp(child_id=data.get('id', None),
                                                                           child_address=data.get('address', None),
                                                                           child_port=data.get('port', None),
                                                                           root_folder=data.get('root_folder', None),
                                                                           root_folder_pages=data.get(
                                                                               'root_folder_pages', None),
                                                                           websocket=ws))

                        elif client_type == 'web':
                            await frontend.handle_message_from_web(data)

                        elif client_type == 'control_app':
                            if client_id is not None and client_id in self.children:
                                await self.children[client_id].handle_message(msg.data)

                        else:
                            logger.error(f"Unknown client type: {client_type}")

                    except Exception as e:
                        logger.error(f"Error processing message of {client_type}:{client_id}: {e}. Data: {data}")

                case web.WSMsgType.ERROR:
                    logger.error("WebSocket error:", ws.exception())

        # Websocket was closed
        try:
            self.clients.remove(ws)
            if client_type == 'control_app':
                self.removeChild(child_id=client_id)
            elif client_type == 'web':
                await frontend.close()
                self.frontends.remove(frontend)

        except Exception as e:
            logger.error("Error removing client:", e)

        return ws

    # ------------------------------------------------------------------------------------------------------------------
    def _getChildByID(self, child_id: str) -> ControlAppChild | None:
        for child in self.children.values():
            if child.child_app_id == child_id:
                return child
        return None

    # ------------------------------------------------------------------------------------------------------------------
    def _getChildByRootFolder(self, child_folder_root: str) -> ControlAppChild | None:
        for child in self.children.values():
            if child.root_folder_id == child_folder_root:
                return child
        return None

    # ------------------------------------------------------------------------------------------------------------------
    async def get_remote_payload(self, child_app_root, child_app_path, page):
        child = self._getChildByRootFolder(child_app_root)
        logger.debug(f"Found child. Getting payload from {child.child_app_id} for {child_app_path}...")
        payload = await child.get_folder_payload(child_app_path, page)

        if payload is None:
            logger.error(f"Could not get payload for {child_app_root}:{child_app_path}")
            return None

        logger.info(f"Got payload for {child_app_root}:{child_app_path}")
        return payload

    # ------------------------------------------------------------------------------------------------------------------
    async def handle_remote_widget_message(self, child_app_root_folder, child_app_path, data):

        child = self._getChildByRootFolder(child_app_root_folder)
        if child is None:
            return None

        # Modify the widget_id to include the child_app_id
        data['id'] = child_app_path

        return_value = await child.handle_widget_message(data)
        return return_value

    @staticmethod
    def _extract_child_subpath(full_path: str, child_root: str) -> Optional[str]:
        """
        Given a full path like '/app:root/folder1/child:rootz/btn1' and a child_root
        like 'child:rootz', return the substring starting with '/child:rootz', e.g.
        '/child:rootz/btn1'. Returns None if child_root isn't found.
        """
        # Build a regex that looks for '/' + child_root, plus the rest of the path (if any)
        pattern = rf'(/' + re.escape(child_root) + r'(?:/.*)?)'
        match = re.search(pattern, full_path)
        return match.group(1) if match else None

    # ------------------------------------------------------------------------------------------------------------------
    async def handle_special_message(self, data: dict):
        """
        Called when the frontend reports a popup click.
        """
        if data.get("event_type") != "popup_response":
            return

        popup_id = data.get("popup_id")
        button_id = data.get("button")
        cb = self._popup_callbacks.pop(popup_id, None)
        if cb:
            cb(button_id)

        # tell *all* frontends to hide it
        await self.broadcast({
            "type": "hide_popup",
            "popup_id": popup_id
        })

    # ------------------------------------------------------------------------------------------------------------------
    async def _registerChildApp(self, child_id, child_address, child_port, root_folder, root_folder_pages, websocket):
        if child_id is None or child_address is None or child_port is None:
            logger.error("Invalid child registration data.")
            return

        if child_id in self.children:
            logger.warning(f"Child {child_id} already registered.")
            return

        self.children[child_id] = ControlAppChild(child_app_id=child_id,
                                                  address=child_address,
                                                  port=child_port,
                                                  root_folder_id=root_folder,
                                                  root_folder_pages=root_folder_pages,
                                                  websocket=websocket,
                                                  app=self)

        logger.info(f"Registered child {child_id} at {child_address}:{child_port}. Root folder: {root_folder}")

    # ------------------------------------------------------------------------------------------------------------------
    async def _connectToParent(self, parent_address, parent_port):
        logger.debug(f"Trying to connect to parent at {parent_address}:{parent_port}")
        self.parent_websocket = None
        self.parent_address = parent_address
        self.parent_port = parent_port

        while not self._exit:
            result = await self.check_target_app_is_up(parent_address, parent_port)
            if result is None:
                await asyncio.sleep(3)
                continue

            logger.debug("Parent App is up")

            # Get the non mDNS address and port from the data
            parent_address_clear = result['address']
            parent_port_clear = result['port']

            ws_url = f"ws://{parent_address_clear}:{parent_port_clear}/ws"
            logger.debug(f"Connecting to parent ws: {ws_url}")
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
                            'id': self.app_id,
                            'root_folder': self.root_group.group_id,
                            'root_folder_pages': self.root_group.pages,
                        }
                        await self.parent_websocket.send_json(payload)

                        # Listen for messages
                        async for msg in parent_ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                await self._handle_message_from_parent(data)
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
    async def _handle_message_from_parent(self, data):
        type = data.get("type", None)

        if type is None:
            logger.warning("Invalid message type received from parent.")

        match type:
            case 'request':
                await self._handle_parent_request(data)
            case 'widget':
                await self.root_group.handle_widget_message(data)
            case 'navigation':
                raise NotImplementedError("Navigation not yet implemented in parent-child communication.")
            case _:
                logger.warning(f"Unknown parent message type: {type}")

    # ------------------------------------------------------------------------------------------------------------------
    async def _handle_parent_request(self, data):
        # raise NotImplementedError(f"Handle parent request not implemented yet")
        request_type = data.get('request_type', None)

        match request_type:
            case 'get_folder_payload':
                path = data.get('folder_path', None)
                page = data.get('page', 0)
                if path:
                    payload = await self.root_group.get_group_payload(path, page)

                    answer = {
                        'type': 'response',
                        'request_id': data.get('request_id', None),
                        'data': payload,
                    }

                    await self.parent_websocket.send_json(answer)

            case 'widget':
                widget_data = data.get('data', None)
                output = await self.root_group.handle_widget_message(widget_data)
                if output is not None:
                    answer = {
                        'type': 'response',
                        'request_id': data.get('request_id', None),
                        'data': output,
                    }
                    await self.parent_websocket.send_json(answer)

            case _:
                logger.warning(f"Unknown request type from parent: {request_type}")

    # ------------------------------------------------------------------------------------------------------------------
    def removeChild(self, child_id):
        if child_id in self.children:
            child = self.children[child_id]
            path = child.root_group.get_path()
            child.close()
            del self.children[child_id]
            for frontend in self.frontends:
                asyncio.create_task(frontend.path_removal_event(path))
            logger.info(f"Removed child {child_id}")

    # ------------------------------------------------------------------------------------------------------------------
    def speak(self, text):
        """
        Send a "speak" command to all connected clients, which will invoke
        the front-end's speak(...) function using the HTML5 SpeechSynthesis API.
        """
        if self.event_loop:
            asyncio.run_coroutine_threadsafe(self._broadcast_speak(text), self.event_loop)
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
        await self.send_to_all_frontends(data)

        if self.parent_websocket is not None:
            msg = {
                'type': 'update_widget',
                'data': data,
            }
            await self.parent_websocket.send_json(msg)

    # ------------------------------------------------------------------------------------------------------------------
    def updateGroup(self, path):
        if self.running:
            asyncio.create_task(self._update_group(path))

    # ------------------------------------------------------------------------------------------------------------------
    async def _update_group(self, path):
        for frontend in self.frontends:
            await frontend.update_group_event(path)

        if self.parent_websocket is not None:
            msg = {
                'type': 'update_group',
                'path': path,
            }
            await self.parent_websocket.send_json(msg)

    # ------------------------------------------------------------------------------------------------------------------
    def updateStatusBar(self):
        if self.running:
            asyncio.create_task(self._updateStatusBar())

    # ------------------------------------------------------------------------------------------------------------------
    async def _updateStatusBar(self):

        payload = await self.status_bar.get_payload()

        message = {
            'type': 'update_status_bar',
            'data': payload
        }

        for frontend in self.frontends:
            await frontend.send_json(message)

    # ------------------------------------------------------------------------------------------------------------------
    def updateStatusBarWidget(self, widget):

        if self.running and self.event_loop is not None:
            asyncio.run_coroutine_threadsafe(
                self._updateStatusBarWidget(widget),
                self.event_loop
            )

    # ------------------------------------------------------------------------------------------------------------------
    async def _updateStatusBarWidget(self, widget):
        payload = await widget.get_payload()
        message = {
            'type': 'update_status_bar_widget',
            'widget_id': widget.widget_id,
            'widget_type': widget.widget_type,
            'data': payload
        }
        for frontend in self.frontends:
            await frontend.send_json(message)

    # ------------------------------------------------------------------------------------------------------------------
    async def send_to_all_frontends(self, message):
        for frontend in self.frontends:
            await frontend.send_json(message)

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
    async def _broadcast_speak(self, text):
        await self.broadcast({
            "type": "speak",
            "text": text
        })

    def popup(
            self,
            text: str,
            buttons: list[dict],
            callback: Callable[[str], None] = None,
            image_base64: Optional[str] = None,
    ):
        """
        Unified popup: optional image.  `callback` gets called with the button‑id.
        """
        popup_id = str(uuid.uuid4())
        if callback is not None:
            self._popup_callbacks[popup_id] = callback

        if self.event_loop:
            asyncio.run_coroutine_threadsafe(
                self._broadcast_popup(popup_id, text, buttons, image_base64),
                self.event_loop
            )
        else:
            asyncio.run(
                self._broadcast_popup(popup_id, text, buttons, image_base64)
            )

    async def _broadcast_popup(
            self,
            popup_id: str,
            text: str,
            buttons: list[dict],
            image: Optional[str] = None
    ):
        msg = {
            "type": "popup",
            "popup_id": popup_id,
            "text": text,
            "buttons": buttons,
        }
        if image is not None:
            msg["image"] = image
        await self.broadcast(msg)
