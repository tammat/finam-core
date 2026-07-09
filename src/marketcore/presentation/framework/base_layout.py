from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from marketcore.presentation.framework.base_section import BaseSection
from marketcore.presentation.framework.registry import LayoutType, UiStatusCode


@dataclass(slots=True)
class BaseLayout:
    layout_id: str
    layout_type: LayoutType

    title_key: str = ""
    subtitle_key: str = ""
    tooltip_key: str = ""

    visible: bool = True
    enabled: bool = True

    order: int = 100
    status_code: UiStatusCode = UiStatusCode.DEFAULT
    status_label_key: str = ""

    sections: tuple[BaseSection, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_visible(self) -> bool:
        return self.visible

    def is_enabled(self) -> bool:
        return self.enabled

    def has_sections(self) -> bool:
        return len(self.sections) > 0

    def visible_sections(self) -> tuple[BaseSection, ...]:
        return tuple(section for section in self.sections if section.is_visible())

    def ordered_sections(self) -> tuple[BaseSection, ...]:
        return tuple(
            sorted(
                self.visible_sections(),
                key=lambda section: (section.order, section.section_id),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "layout_id": self.layout_id,
            "layout_type": self.layout_type.value,
            "title_key": self.title_key,
            "subtitle_key": self.subtitle_key,
            "tooltip_key": self.tooltip_key,
            "visible": self.visible,
            "enabled": self.enabled,
            "order": self.order,
            "status_code": self.status_code.value,
            "status_label_key": self.status_label_key,
            "sections": [section.to_dict() for section in self.ordered_sections()],
            "metadata": self.metadata,
        }
