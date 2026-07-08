from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class WidgetViewModel:
    widget_id: str
    title_key: str
    icon: str
    priority: int
    category: str = "general"
    state: str = "readonly"
    content: dict[str, Any] = field(default_factory=dict)
    actions: list[dict[str, Any]] = field(default_factory=list)
    updated_at: str = ""


@dataclass(frozen=True)
class WidgetDefinition:
    widget_id: str
    title_key: str
    icon: str
    priority: int
    category: str
