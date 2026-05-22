from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TradeContextSnapshot:
    closed_trade_id: int
    symbol: str
    strategy: str
    timeframe: str
    trade_source: str

    entry_ts: datetime | None
    exit_ts: datetime | None

    regime: str
    trend: str
    volatility: str

    heat_status: str
    portfolio_risk_multiplier: float

    exit_policy: str
    lifecycle_state: str

    signal_score: float
    risk_reward: float

    context_quality: str
    missing_fields: str
