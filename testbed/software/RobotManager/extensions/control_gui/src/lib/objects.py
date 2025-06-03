from __future__ import annotations

import abc
from typing import Any

from core.utils.logging_utils import Logger
from extensions.control_gui.src.lib.utilities import check_for_spaces, split_path


# ======================================================================================================================
class GUI_Object(abc.ABC):
    id: str
    uid: str
    type: str
    parent: Any

    config: dict

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, widget_id):

        if check_for_spaces(widget_id):
            raise ValueError(f"Object id '{widget_id}' contains spaces")

        self.parent = None
        self.id = widget_id

        self.logger = Logger(self.id, 'DEBUG')

    # ------------------------------------------------------------------------------------------------------------------
    def sendUpdate(self, data):
        message = {
            'type': 'update',
            'id': self.uid,
            'data': data
        }

        gui = self.getGUI()
        if gui is not None:
            try:
                gui.broadcast(message)
            except Exception as e:
                self.logger.error(f"Error sending update: {e}")

    # ------------------------------------------------------------------------------------------------------------------
    def getGUI(self):
        if self.parent:
            return self.parent.getGUI()
        return None

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def getConfiguration(self) -> dict:
        ...

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def onMessage(self, message) -> Any:
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def update(self, **kwargs):
        # Go through all kwargs and update the config if the key is in the config
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
            elif hasattr(self, key):
                setattr(self, key, value)

        self.sendUpdate(self.getConfiguration())

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def init(self, *args, **kwargs):
        ...

    # ------------------------------------------------------------------------------------------------------------------
    def getPayload(self):
        payload = {
            'id': self.uid,
            'type': self.type,
            'config': self.getConfiguration(),
        }
        return payload

    # ------------------------------------------------------------------------------------------------------------------
    @property
    def uid(self):
        uid = self.id
        if self.parent is not None:
            uid = f"{self.parent.uid}/{uid}"
        return uid


# ======================================================================================================================
class GUI_Object_Group(GUI_Object):
    group_id: str
    objects: dict[str, GUI_Object]

    def __init__(self, group_id):
        super().__init__(group_id)

    def addObject(self, obj: GUI_Object):
        self.objects[obj.id] = obj
        obj.parent = self

    # ------------------------------------------------------------------------------------------------------------------
    def getObjectByPath(self, path: str) -> GUI_Object | GUI_Object_Group | None:
        """
        Recursively retrieve an object (or sub‐group) inside this group by a slash‐delimited path.
        e.g. if path = "childGroup/grandchildObject", it first finds 'childGroup' in self.objects,
        then calls childGroup.getObjectByPath("grandchildObject").
        """
        # Trim leading/trailing slashes, split into first‐and‐remainder
        first_segment, remainder = split_path(path)

        if not first_segment:
            # If path was empty or just "/", no object to return
            return None

        # Find a direct child with id == first_segment
        if first_segment not in self.objects:
            return None

        child = self.objects[first_segment]
        if not remainder:
            # No more sub‐path: return the child itself
            return child

        # remainder exists → only works if child is also a GUI_Object_Group
        if isinstance(child, GUI_Object_Group):
            return child.getObjectByPath(remainder)
        else:
            # asked for deeper path but child is not a group
            return None

    # ------------------------------------------------------------------------------------------------------------------
    def getConfiguration(self) -> dict:
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def getData(self) -> dict:
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def onMessage(self, message) -> Any:
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def update(self, *args, **kwargs):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def init(self, *args, **kwargs):
        pass
