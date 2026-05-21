from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IncrementalExitInput:
    symbol: str
    strategy: str
    timeframe: str
    side: str
    entry_price: float
    current_price: float
    qty: float
    take_distance: float
    stop_distance: float


@dataclass(frozen=True)
class IncrementalExitAdvice:
    symbol: str
    strategy: str
    timeframe: str
    side: str
    unrealized_move: float
    distance_to_take: float
    distance_to_stop: float
    take_price: float
    stop_price: float
    action: str
    reason: str


def build_incremental_exit_advice(item: IncrementalExitInput) -> IncrementalExitAdvice:
    side = item.side.lower().strip()

    if side in {"buy", "long"}:
        unrealized_move = item.current_price - item.entry_price
        take_price = item.entry_price + abs(item.take_distance)
        stop_price = item.entry_price - abs(item.stop_distance)
        distance_to_take = take_price - item.current_price
        distance_to_stop = item.current_price - stop_price

    elif side in {"sell", "short"}:
        unrealized_move = item.entry_price - item.current_price
        take_price = item.entry_price - abs(item.take_distance)
        stop_price = item.entry_price + abs(item.stop_distance)
        distance_to_take = item.current_price - take_price
        distance_to_stop = stop_price - item.current_price

    else:
        return IncrementalExitAdvice(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            side=side,
            unrealized_move=0.0,
            distance_to_take=0.0,
            distance_to_stop=0.0,
            take_price=0.0,
            stop_price=0.0,
            action="NO_ADVICE",
            reason="unknown_side",
        )

    action = "HOLD"
    reason = "inside_exit_band"

    if distance_to_take <= 0:
        action = "TAKE_ZONE"
        reason = "current_price_reached_or_exceeded_advisory_take"
    elif distance_to_stop <= 0:
        action = "STOP_ZONE"
        reason = "current_price_reached_or_exceeded_advisory_stop"
    elif unrealized_move > 0 and distance_to_take < abs(item.take_distance) * 0.25:
        action = "NEAR_TAKE"
        reason = "price_near_advisory_take"
    elif unrealized_move < 0 and distance_to_stop < abs(item.stop_distance) * 0.25:
        action = "NEAR_STOP"
        reason = "price_near_advisory_stop"

    return IncrementalExitAdvice(
        symbol=item.symbol,
        strategy=item.strategy,
        timeframe=item.timeframe,
        side=side,
        unrealized_move=round(unrealized_move, 10),
        distance_to_take=round(distance_to_take, 10),
        distance_to_stop=round(distance_to_stop, 10),
        take_price=round(take_price, 10),
        stop_price=round(stop_price, 10),
        action=action,
        reason=reason,
    )
