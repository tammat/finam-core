from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from marketcore.presentation.framework.base_card import BaseCard
from marketcore.presentation.framework.registry import SectionType, UiStatusCode


@dataclass(slots=True)
class BaseSection:
    section_id: str
    section_type: SectionType

    title_key: str = ""
    subtitle_key: str = ""
    tooltip_key: str = ""

    visible: bool = True
    enabled: bool = True

    order: int = 100
    status_code: UiStatusCode = UiStatusCode.DEFAULT
    status_label_key: str = ""

    cards: tuple[BaseCard, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_visible(self) -> bool:
        return self.visible

    def is_enabled(self) -> bool:
        return self.enabled

    def has_cards(self) -> bool:
        return len(self.cards) > 0

    def visible_cards(self) -> tuple[BaseCard, ...]:
        return tuple(card for card in self.cards if card.is_visible())

    def ordered_cards(self) -> tuple[BaseCard, ...]:
        return tuple(sorted(self.visible_cards(), key=lambda card: (card.priority, card.order, card.widget_id)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "section_type": self.section_type.value,
            "title_key": self.title_key,
            "subtitle_key": self.subtitle_key,
            "tooltip_key": self.tooltip_key,
            "visible": self.visible,
            "enabled": self.enabled,
            "order": self.order,
            "status_code": self.status_code.value,
            "status_label_key": self.status_label_key,
            "cards": [card.to_dict() for card in self.ordered_cards()],
            "metadata": self.metadata,
        }
