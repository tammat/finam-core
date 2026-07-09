from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from marketcore.presentation.framework.registry import WidgetType


@dataclass(slots=True)
class BaseWidget:
    widget_id: str
    widget_type: WidgetType

    title_key: str = ""
    subtitle_key: str = ""

    visible: bool = True
    enabled: bool = True

    order: int = 100

    icon_key: str = ""
    tooltip_key: str = ""

    css_classes: tuple[str, ...] = ()

    metadata: dict[str, Any] = field(default_factory=dict)

    def is_visible(self) -> bool:
        return self.visible

    def is_enabled(self) -> bool:
        return self.enabled

    def to_dict(self) -> dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type.value,
            "title_key": self.title_key,
            "subtitle_key": self.subtitle_key,
            "visible": self.visible,
            "enabled": self.enabled,
            "order": self.order,
            "icon_key": self.icon_key,
            "tooltip_key": self.tooltip_key,
            "css_classes": list(self.css_classes),
            "metadata": self.metadata,
        }
