from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InstrumentCardViewModelV1:
    title: str
    subtitle: str
    badge: str
    status: str
    icon: str
    tooltip: str
    navigation_target: str
    source_table: str
    fallback_used: bool
