from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecommendationWidgetViewModel:
    widget_id: str
    title_key: str
    recommendation_key: str
    confidence_text: str
    reason_keys: list[str]
    state: str
