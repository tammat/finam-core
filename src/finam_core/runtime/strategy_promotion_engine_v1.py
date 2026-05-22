from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyPromotionEngineInput:
    symbol: str
    strategy: str
    timeframe: str
    trade_source: str
    trades: int
    profit_factor: float
    expectancy: float
    winrate: float
    quality_full_ratio: float
    quality_partial_ratio: float
    risk_context_weak_ratio: float
    score: float
    rank_status: str
    fill_quality_status: str
    reconstruction_allowed: bool
    lifecycle_state: str


@dataclass(frozen=True)
class StrategyPromotionEngineDecision:
    symbol: str
    strategy: str
    timeframe: str
    trade_source: str
    decision: str
    target_lifecycle_state: str
    allow_runtime: bool
    allow_radar: bool
    allow_research: bool
    reason: str


def decide_strategy_promotion_v1(
    item: StrategyPromotionEngineInput,
) -> StrategyPromotionEngineDecision:
    """
    Русский комментарий:
    Promotion Engine v1.
    Решает, можно ли повышать стратегию в PAPER,
    оставлять в RADAR/RESEARCH или блокировать.
    """

    if not item.reconstruction_allowed and item.fill_quality_status != "UNKNOWN":
        return StrategyPromotionEngineDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            trade_source=item.trade_source,
            decision="BLOCK",
            target_lifecycle_state="BLOCKED",
            allow_runtime=False,
            allow_radar=False,
            allow_research=False,
            reason=f"качество_fill_не_позволяет_reconstruction:{item.fill_quality_status}",
        )

    if item.trades < 20:
        return StrategyPromotionEngineDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            trade_source=item.trade_source,
            decision="KEEP_RESEARCH",
            target_lifecycle_state="RESEARCH",
            allow_runtime=False,
            allow_radar=False,
            allow_research=True,
            reason="малая_выборка_для_promotion",
        )

    if item.rank_status in {"REJECT", "WEAK", "NO_TRADES"}:
        return StrategyPromotionEngineDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            trade_source=item.trade_source,
            decision="BLOCK",
            target_lifecycle_state="BLOCKED",
            allow_runtime=False,
            allow_radar=False,
            allow_research=False,
            reason=f"слабый_rank_status:{item.rank_status}",
        )

    if (
        item.profit_factor >= 1.3
        and item.expectancy > 0
        and item.score >= 25
        and item.quality_full_ratio > 0
        and item.risk_context_weak_ratio <= 0.25
    ):
        return StrategyPromotionEngineDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            trade_source=item.trade_source,
            decision="PROMOTE_TO_PAPER",
            target_lifecycle_state="PAPER",
            allow_runtime=True,
            allow_radar=True,
            allow_research=True,
            reason="стратегия_допущена_к_paper_по_статистике",
        )

    if item.profit_factor >= 1.0 and item.expectancy >= 0:
        return StrategyPromotionEngineDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            trade_source=item.trade_source,
            decision="DEMOTE_TO_RADAR",
            target_lifecycle_state="RADAR",
            allow_runtime=False,
            allow_radar=True,
            allow_research=True,
            reason="стратегия_оставлена_в_radar_без_runtime",
        )

    return StrategyPromotionEngineDecision(
        symbol=item.symbol,
        strategy=item.strategy,
        timeframe=item.timeframe,
        trade_source=item.trade_source,
        decision="KEEP_RESEARCH",
        target_lifecycle_state="RESEARCH",
        allow_runtime=False,
        allow_radar=False,
        allow_research=True,
        reason="нет_достаточного_основания_для_paper",
    )
