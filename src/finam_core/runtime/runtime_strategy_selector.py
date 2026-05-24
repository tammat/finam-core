from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeStrategyCandidate:
    symbol: str
    strategy: str
    timeframe: str
    trade_source: str
    runtime_action: str
    allow_paper_signal: bool
    allow_radar_signal: bool
    allow_real_suggestion: bool


@dataclass(frozen=True)
class RuntimeStrategySelection:
    symbol: str
    strategy: str
    timeframe: str
    mode: str
    enabled: bool
    reason: str


def select_runtime_strategy(
    item: RuntimeStrategyCandidate,
) -> RuntimeStrategySelection:
    """
    Русский комментарий:
    Runtime selector не принимает торговых решений.
    Он только определяет режим допуска стратегии.
    """

    action = item.runtime_action.upper().strip()

    if action in ("PROMOTE", "PAPER_RUNTIME_CANDIDATE") and item.allow_paper_signal:
        return RuntimeStrategySelection(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            mode="PAPER_ENABLED",
            enabled=True,
            reason="стратегия_допущена_к_paper_runtime",
        )

    if action == "WATCH" and item.allow_radar_signal:
        return RuntimeStrategySelection(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            mode="RADAR_ONLY",
            enabled=True,
            reason="стратегия_только_для_наблюдения",
        )

    if action == "RESEARCH_WATCH" and item.allow_radar_signal:
        return RuntimeStrategySelection(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            mode="RESEARCH_WATCH",
            enabled=False,
            reason="стратегия_в_research_watch_без_runtime",
        )

    if action == "RESEARCH_ONLY":
        return RuntimeStrategySelection(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            mode="RESEARCH_ONLY",
            enabled=False,
            reason="стратегия_оставлена_только_для_исследований",
        )

    if action == "BLOCK":
        return RuntimeStrategySelection(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            mode="BLOCKED",
            enabled=False,
            reason="стратегия_заблокирована_по_статистике",
        )

    return RuntimeStrategySelection(
        symbol=item.symbol,
        strategy=item.strategy,
        timeframe=item.timeframe,
        mode="UNKNOWN",
        enabled=False,
        reason=f"неизвестный_runtime_action:{item.runtime_action}",
    )
