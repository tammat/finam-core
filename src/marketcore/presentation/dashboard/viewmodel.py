from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolbarItem:
    key: str
    label_key: str
    icon: str = ""
    href: str = ""
    disabled: bool = False
    action_type: str = "navigation"


@dataclass(frozen=True)
class KpiItem:
    key: str
    label_key: str
    value: Any
    hint_key: str = ""
    tone: str = "neutral"
    icon: str = ""


@dataclass(frozen=True)
class AlertItem:
    key: str
    label_key: str
    message_key: str
    tone: str = "info"
    icon: str = ""


@dataclass(frozen=True)
class TableColumn:
    key: str
    label_key: str
    value_type: str = "text"
    sortable: bool = False
    align: str = "left"


@dataclass(frozen=True)
class TableModel:
    columns: list[TableColumn] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    rows_count: int = 0
    empty_message_key: str = "message.empty"


@dataclass(frozen=True)
class SafetyModel:
    runtime_allowed: int = 0
    execution_allowed: int = 0
    micro_live_allowed: int = 0
    orders_changed: int = 0
    fills_changed: int = 0


@dataclass(frozen=True)
class DashboardViewModel:
    dashboard_id: str
    title_key: str
    subtitle_key: str = ""
    icon: str = ""
    updated_at: str = ""
    toolbar: list[ToolbarItem] = field(default_factory=list)
    kpis: list[KpiItem] = field(default_factory=list)
    alerts: list[AlertItem] = field(default_factory=list)
    table: TableModel = field(default_factory=TableModel)
    footer: dict[str, Any] = field(default_factory=dict)
    safety: SafetyModel = field(default_factory=SafetyModel)
