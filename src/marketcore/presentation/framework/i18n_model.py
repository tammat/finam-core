from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UiTextModel:
    resource_key: str
    locale_code: str
    caption: str
    caption_short: str
    caption_mobile: str
    tooltip: str
    icon: str
