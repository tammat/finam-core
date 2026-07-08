from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class RecommendationExecutionContext:

    recommendation_id: int

    direction_code: str

    entry_price: Decimal

    invalidation_price: Decimal

    target_price: Decimal

    stop_loss_price: Decimal

    take_profit_price: Decimal

    trailing_enabled: bool

    trailing_step: Decimal

    trailing_activation_price: Decimal

    horizon_bars: int

    risk_unit: Decimal

    source_context_id: int

    source_edge_context_id: int

    evidence: dict[str, Any]
