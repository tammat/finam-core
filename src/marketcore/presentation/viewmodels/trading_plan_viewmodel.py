from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TradingPlanWidgetViewModel:
    widget_id: str
    title_key: str
    direction_key: str
    entry_price: str
    stop_price: str
    target_price: str
    horizon_bars: str
    risk_unit: str
    profile_code: str
    entry_source_key: str
    stop_source_key: str
    target_source_key: str
    state: str
