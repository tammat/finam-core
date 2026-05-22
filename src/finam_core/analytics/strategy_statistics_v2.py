from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyTradeSampleV2:
    pnl: float
    attribution_quality: str
    heat_status: str
    lifecycle_action: str


@dataclass(frozen=True)
class StrategyStatisticsV2:
    symbol: str
    strategy: str
    timeframe: str
    trade_source: str
    trades: int
    wins: int
    losses: int
    winrate: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    expectancy: float
    quality_full_ratio: float
    quality_partial_ratio: float
    risk_context_weak_ratio: float
    high_heat_ratio: float
    lifecycle_problem_ratio: float
    status: str


def calculate_strategy_statistics_v2(
    *,
    symbol: str,
    strategy: str,
    timeframe: str,
    trade_source: str,
    trades: list[StrategyTradeSampleV2],
) -> StrategyStatisticsV2:
    total = len(trades)

    if total == 0:
        return StrategyStatisticsV2(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            trade_source=trade_source,
            trades=0,
            wins=0,
            losses=0,
            winrate=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            profit_factor=0.0,
            expectancy=0.0,
            quality_full_ratio=0.0,
            quality_partial_ratio=0.0,
            risk_context_weak_ratio=0.0,
            high_heat_ratio=0.0,
            lifecycle_problem_ratio=0.0,
            status="NO_TRADES",
        )

    wins = [x for x in trades if x.pnl > 0]
    losses = [x for x in trades if x.pnl < 0]

    gross_profit = sum(x.pnl for x in wins)
    gross_loss_abs = abs(sum(x.pnl for x in losses))

    profit_factor = gross_profit / gross_loss_abs if gross_loss_abs > 0 else 999.0
    expectancy = sum(x.pnl for x in trades) / total

    full = sum(1 for x in trades if x.attribution_quality == "FULL")
    partial = sum(1 for x in trades if x.attribution_quality == "PARTIAL")
    weak = sum(1 for x in trades if x.attribution_quality == "RISK_CONTEXT_WEAK")
    high_heat = sum(1 for x in trades if x.heat_status in {"HIGH", "CRITICAL", "EXTREME"})
    lifecycle_problem = sum(
        1
        for x in trades
        if x.lifecycle_action in {"SYNC_LIFECYCLE_QTY", "REBUILD_LIFECYCLE_STATE"}
    )

    if total < 20:
        status = "LOW_SAMPLE"
    elif expectancy <= 0 or profit_factor < 1.0:
        status = "WEAK"
    elif weak / total > 0.25:
        status = "WEAK_CONTEXT"
    elif profit_factor >= 1.3 and expectancy > 0:
        status = "PROMISING"
    else:
        status = "NEUTRAL"

    return StrategyStatisticsV2(
        symbol=symbol,
        strategy=strategy,
        timeframe=timeframe,
        trade_source=trade_source,
        trades=total,
        wins=len(wins),
        losses=len(losses),
        winrate=len(wins) / total,
        gross_profit=gross_profit,
        gross_loss=gross_loss_abs,
        profit_factor=profit_factor,
        expectancy=expectancy,
        quality_full_ratio=full / total,
        quality_partial_ratio=partial / total,
        risk_context_weak_ratio=weak / total,
        high_heat_ratio=high_heat / total,
        lifecycle_problem_ratio=lifecycle_problem / total,
        status=status,
    )
