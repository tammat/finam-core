from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class RecommendationContext:
    symbol: str
    timeframe: str
    edge_score: Decimal
    market_context_id: int
    edge_context_id: int
    knowledge_coverage: Decimal
    regime_code: str
    volatility_state: str
    liquidity_state: str
    volume_state: str
    spread_state: str
    session_state: str
    correlation_state: str
    sector_strength_state: str
    relationships: list[dict[str, Any]]
