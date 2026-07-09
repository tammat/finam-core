from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BaseWidget:
    widget_id: str
    widget_type: str

    title: str = ""
    subtitle: str = ""

    visible: bool = True
    enabled: bool = True

    order: int = 100

    icon: str = ""

    tooltip: str = ""

    css_classes: tuple[str, ...] = ()

    metadata: dict[str, Any] = field(default_factory=dict)

    def is_visible(self) -> bool:
        return self.visible

    def is_enabled(self) -> bool:
        return self.enabled

    def to_dict(self) -> dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type,
            "title": self.title,
            "subtitle": self.subtitle,
            "visible": self.visible,
            "enabled": self.enabled,
            "order": self.order,
            "icon": self.icon,
            "tooltip": self.tooltip,
            "css_classes": list(self.css_classes),
            "metadata": self.metadata,
        }
