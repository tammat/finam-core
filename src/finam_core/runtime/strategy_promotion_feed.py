from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyPromotionInput:
    symbol: str
    strategy: str
    timeframe: str
    trade_source: str
    score: float
    rank_status: str
    reason: str


@dataclass(frozen=True)
class StrategyPromotionDecision:
    symbol: str
    strategy: str
    timeframe: str
    trade_source: str
    runtime_action: str
    allow_paper_signal: bool
    allow_radar_signal: bool
    allow_real_suggestion: bool
    reason: str


def build_strategy_promotion_decision(
    item: StrategyPromotionInput,
) -> StrategyPromotionDecision:
    status = item.rank_status.upper().strip()

    if status == "CANDIDATE":
        return StrategyPromotionDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            trade_source=item.trade_source,
            runtime_action="PAPER_CANDIDATE",
            allow_paper_signal=True,
            allow_radar_signal=True,
            allow_real_suggestion=False,
            reason=f"paper_candidate_from_research_verdict:{item.reason}",
        )

    if status == "PROMOTE":
        return StrategyPromotionDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            trade_source=item.trade_source,
            runtime_action="PROMOTE",
            allow_paper_signal=True,
            allow_radar_signal=True,
            allow_real_suggestion=False,
            reason="стратегия_допущена_в_paper_и_radar",
        )

    if status == "WATCH":
        return StrategyPromotionDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            trade_source=item.trade_source,
            runtime_action="WATCH",
            allow_paper_signal=False,
            allow_radar_signal=True,
            allow_real_suggestion=False,
            reason="только_наблюдение_без_paper_signal",
        )

    if status == "WATCH_LOW_SAMPLE":
        return StrategyPromotionDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            trade_source=item.trade_source,
            runtime_action="RESEARCH_ONLY",
            allow_paper_signal=False,
            allow_radar_signal=False,
            allow_real_suggestion=False,
            reason="малая_выборка_только_research",
        )

    if status == "WATCH_DIVERGENCE":
        return StrategyPromotionDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            trade_source=item.trade_source,
            runtime_action="RESEARCH_WATCH",
            allow_paper_signal=False,
            allow_radar_signal=True,
            allow_real_suggestion=False,
            reason="research_watch_divergence",
        )

    # Русский комментарий:
    # PLZL D1 стратегии подтверждены attribution-chain статистикой, но не должны
    # получать paper/real-допуск. Держим их в безопасном research/radar watch.
    if (
        status in {"REJECT", "WEAK", "NO_TRADES"}
        and item.symbol == "PLZL@MISX"
        and item.strategy in {"MOEX_SIMPLE_MOMENTUM", "MOEX_MEAN_REVERSION_V1"}
        and item.timeframe == "D1"
    ):
        return StrategyPromotionDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            trade_source=item.trade_source,
            runtime_action="RESEARCH_WATCH",
            allow_paper_signal=False,
            allow_radar_signal=True,
            allow_real_suggestion=False,
            reason=f"plzl_attribution_chain_research_watch:{item.reason}",
        )

    if status in {"REJECT", "WEAK", "NO_TRADES"}:
        return StrategyPromotionDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            trade_source=item.trade_source,
            runtime_action="BLOCK",
            allow_paper_signal=False,
            allow_radar_signal=False,
            allow_real_suggestion=False,
            reason="стратегия_заблокирована_по_статистике",
        )

    return StrategyPromotionDecision(
        symbol=item.symbol,
        strategy=item.strategy,
        timeframe=item.timeframe,
        trade_source=item.trade_source,
        runtime_action="UNKNOWN",
        allow_paper_signal=False,
        allow_radar_signal=False,
        allow_real_suggestion=False,
        reason=f"неизвестный_rank_status:{item.rank_status}",
    )
