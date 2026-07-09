from __future__ import annotations

from dataclasses import dataclass

from marketcore.presentation.framework.registry import UiStatusCode


@dataclass(frozen=True, slots=True)
class InstrumentCardViewModelV1:
    title_key: str
    subtitle_key: str
    badge_key: str
    status_code: UiStatusCode
    icon_key: str
    tooltip_key: str
    navigation_target: str
    source_table: str
    fallback_used: bool
