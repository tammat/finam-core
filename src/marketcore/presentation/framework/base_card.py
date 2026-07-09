from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from marketcore.presentation.framework.base_widget import BaseWidget
from marketcore.presentation.framework.registry import CardType, UiStatusCode, WidgetType


@dataclass(slots=True)
class BaseCard(BaseWidget):
    card_type: CardType = CardType.BASE
    status_code: UiStatusCode = UiStatusCode.DEFAULT
    status_label_key: str = ""
    priority: int = 100
    actions: tuple[dict[str, Any], ...] = ()
    badges: tuple[dict[str, Any], ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.widget_type != WidgetType.BASE and self.widget_type != WidgetType.KPI:
            return

    def has_actions(self) -> bool:
        return len(self.actions) > 0

    def has_badges(self) -> bool:
        return len(self.badges) > 0

    def to_dict(self) -> dict[str, Any]:
        data = BaseWidget.to_dict(self)
        data.update(
            {
                "card_type": self.card_type.value,
                "status_code": self.status_code.value,
                "status_label_key": self.status_label_key,
                "priority": self.priority,
                "actions": list(self.actions),
                "badges": list(self.badges),
                "payload": self.payload,
            }
        )
        return data
