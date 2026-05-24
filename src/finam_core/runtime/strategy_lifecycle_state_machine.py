from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyLifecycleInput:
    symbol: str
    strategy: str
    timeframe: str
    runtime_action: str
    score: float
    rank_status: str


@dataclass(frozen=True)
class StrategyLifecycleDecision:
    symbol: str
    strategy: str
    timeframe: str
    lifecycle_state: str
    allow_runtime: bool
    allow_radar: bool
    allow_research: bool
    reason: str


def decide_strategy_lifecycle(item: StrategyLifecycleInput) -> StrategyLifecycleDecision:
    """
    Русский комментарий:
    Машина состояний стратегии.
    Пока read-only/advisory: не исполняет сделки и не меняет RiskStack.
    """

    action = item.runtime_action.upper().strip()
    rank = item.rank_status.upper().strip()

    if action == "PROMOTE":
        return StrategyLifecycleDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            lifecycle_state="PAPER",
            allow_runtime=True,
            allow_radar=True,
            allow_research=True,
            reason="стратегия_допущена_к_paper_runtime",
        )

    if action == "WATCH":
        return StrategyLifecycleDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            lifecycle_state="RADAR",
            allow_runtime=False,
            allow_radar=True,
            allow_research=True,
            reason="стратегия_только_для_наблюдения",
        )

    if action == "RESEARCH_WATCH":
        return StrategyLifecycleDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            lifecycle_state="RESEARCH_WATCH",
            allow_runtime=False,
            allow_radar=True,
            allow_research=True,
            reason="стратегия_в_research_watch_без_runtime",
        )

    if action == "RESEARCH_ONLY":
        return StrategyLifecycleDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            lifecycle_state="RESEARCH",
            allow_runtime=False,
            allow_radar=False,
            allow_research=True,
            reason="стратегия_только_для_исследований",
        )

    if action == "BLOCK":
        return StrategyLifecycleDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            lifecycle_state="BLOCKED",
            allow_runtime=False,
            allow_radar=False,
            allow_research=False,
            reason="стратегия_заблокирована",
        )

    if rank in {"WEAK", "REJECT"}:
        return StrategyLifecycleDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            lifecycle_state="QUARANTINE",
            allow_runtime=False,
            allow_radar=False,
            allow_research=True,
            reason="стратегия_в_карантине_из-за_слабой_статистики",
        )

    return StrategyLifecycleDecision(
        symbol=item.symbol,
        strategy=item.strategy,
        timeframe=item.timeframe,
        lifecycle_state="UNKNOWN",
        allow_runtime=False,
        allow_radar=False,
        allow_research=False,
        reason=f"неизвестное_состояние:runtime_action={item.runtime_action};rank_status={item.rank_status}",
    )
