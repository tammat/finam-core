from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class FuturesEntryCostDecisionV1:
    allowed: bool
    reason_code: str
    expected_move_rub: float
    estimated_cost_rub: float
    required_move_rub: float


def evaluate_futures_entry_cost_gate_v1(
    *,
    entry_price: float,
    target_price: float,
    qty: float,
    best_bid: float,
    best_ask: float,
    quote_observed_at: datetime,
    min_price_step: float,
    step_value: float,
    round_trip_commission_rub: float,
    minimum_cost_buffer: float,
    max_quote_age_seconds: int = 300,
    slippage_spreads: float = 0.5,
    now: datetime | None = None,
) -> FuturesEntryCostDecisionV1:
    """Проверяет экономику фьючерсного входа в рублях одного контракта."""
    entry = float(entry_price or 0.0)
    target = float(target_price or 0.0)
    quantity = abs(float(qty or 0.0))
    bid = float(best_bid or 0.0)
    ask = float(best_ask or 0.0)
    tick = float(min_price_step or 0.0)
    tick_value = float(step_value or 0.0)

    if entry <= 0 or target <= 0 or quantity <= 0:
        return FuturesEntryCostDecisionV1(
            False, "EXPECTED_MOVE_UNAVAILABLE", 0.0, 0.0, 0.0
        )
    if tick <= 0 or tick_value <= 0:
        return FuturesEntryCostDecisionV1(
            False, "FUTURES_SPEC_UNAVAILABLE", 0.0, 0.0, 0.0
        )
    if bid <= 0 or ask <= bid:
        return FuturesEntryCostDecisionV1(
            False, "MICROSTRUCTURE_UNAVAILABLE", 0.0, 0.0, 0.0
        )

    observed = quote_observed_at
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    if (current - observed).total_seconds() > max(1, int(max_quote_age_seconds)):
        return FuturesEntryCostDecisionV1(
            False, "MICROSTRUCTURE_STALE", 0.0, 0.0, 0.0
        )

    expected_ticks = abs(target - entry) / tick
    spread_ticks = (ask - bid) / tick
    expected_move = expected_ticks * tick_value * quantity
    spread_cost = spread_ticks * tick_value * quantity
    estimated_cost = max(float(round_trip_commission_rub or 0.0), 0.0)
    estimated_cost += spread_cost * (1.0 + max(float(slippage_spreads), 0.0))
    required_move = estimated_cost * max(float(minimum_cost_buffer or 1.0), 1.0)
    allowed = expected_move > required_move

    return FuturesEntryCostDecisionV1(
        allowed=allowed,
        reason_code=(
            "FUTURES_COST_BUFFER_PASS"
            if allowed
            else "EXPECTED_MOVE_BELOW_FUTURES_COST_BUFFER"
        ),
        expected_move_rub=expected_move,
        estimated_cost_rub=estimated_cost,
        required_move_rub=required_move,
    )
