from __future__ import annotations

import abc
from typing import Any


# ======================================================================================================================
class GUI_Object(abc.ABC):
    widget_id: str
    uid: str
    group: GUI_Object_Group

    def __init__(self):
        ...

    @abc.abstractmethod
    def getConfiguration(self) -> dict:
        ...

    @abc.abstractmethod
    def getData(self) -> dict:
        ...

    @abc.abstractmethod
    def onMessage(self, message) -> Any:
        ...

    @abc.abstractmethod
    def update(self, *args, **kwargs):
        ...

    @abc.abstractmethod
    def init(self, *args, **kwargs):
        ...

    @property
    def uid(self):
        uid = self.widget_id
        parent = self.group
        while parent is not None:
            uid = f"{parent.group_id}/{uid}"
            parent = parent.parent_group
        return f"/{uid}"

# ======================================================================================================================
class GUI_Object_Group:
    group_id: str

    child_groups: list[GUI_Object_Group]
    parent_group: GUI_Object_Group | None

    is_root: bool = False

    def __init__(self):
        ...