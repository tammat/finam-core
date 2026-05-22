from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TradeFillQualityInput:
    symbol: str
    trade_source: str
    total_fills: int
    buy_fills: int
    sell_fills: int
    missing_strategy: int
    missing_timeframe: int
    backfill_fills: int


@dataclass(frozen=True)
class TradeFillQualityDecision:
    symbol: str
    trade_source: str
    total_fills: int
    buy_fills: int
    sell_fills: int
    missing_strategy: int
    missing_timeframe: int
    backfill_fills: int
    status: str
    reconstruction_allowed: bool
    reason: str


def audit_trade_fill_quality(item: TradeFillQualityInput) -> TradeFillQualityDecision:
    if item.total_fills <= 0:
        status = "NO_FILLS"
        allowed = False
        reason = "нет_fill_данных"

    elif item.buy_fills == 0 or item.sell_fills == 0:
        status = "ONE_SIDED_FILLS"
        allowed = False
        reason = "есть_только_одна_сторона_сделок"

    elif item.missing_strategy / item.total_fills > 0.8:
        status = "MISSING_STRATEGY_CONTEXT"
        allowed = False
        reason = "почти_все_fill_без_strategy"

    elif item.missing_timeframe / item.total_fills > 0.8:
        status = "MISSING_TIMEFRAME_CONTEXT"
        allowed = False
        reason = "почти_все_fill_без_timeframe"

    elif item.backfill_fills / item.total_fills > 0.8:
        status = "BACKFILL_DOMINATED"
        allowed = False
        reason = "fill_данные_почти_полностью_из_backfill"

    else:
        status = "RECONSTRUCTION_ALLOWED"
        allowed = True
        reason = "качество_fill_достаточно_для_reconstruction"

    return TradeFillQualityDecision(
        symbol=item.symbol,
        trade_source=item.trade_source,
        total_fills=item.total_fills,
        buy_fills=item.buy_fills,
        sell_fills=item.sell_fills,
        missing_strategy=item.missing_strategy,
        missing_timeframe=item.missing_timeframe,
        backfill_fills=item.backfill_fills,
        status=status,
        reconstruction_allowed=allowed,
        reason=reason,
    )
