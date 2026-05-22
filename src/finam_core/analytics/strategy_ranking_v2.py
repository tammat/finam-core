from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyRankingInputV2:
    symbol: str
    strategy: str
    timeframe: str
    trade_source: str
    trades: int
    profit_factor: float
    winrate: float
    expectancy: float
    quality_full_ratio: float
    risk_context_weak_ratio: float
    high_heat_ratio: float
    lifecycle_problem_ratio: float
    status: str


@dataclass(frozen=True)
class StrategyRankingDecisionV2:
    symbol: str
    strategy: str
    timeframe: str
    trade_source: str
    score: float
    rank_status: str
    reason: str


def calculate_strategy_rank_v2(item: StrategyRankingInputV2) -> StrategyRankingDecisionV2:
    """
    Русский комментарий:
    Рейтинг стратегии v2.
    Не допускает продвижение стратегии только по прибыли,
    если выборка маленькая или слабое качество контекста.
    """

    trades = int(item.trades)

    if trades <= 0:
        return StrategyRankingDecisionV2(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            trade_source=item.trade_source,
            score=0.0,
            rank_status="NO_TRADES",
            reason="нет_сделок",
        )

    sample_factor = min(trades / 50.0, 1.0)

    pf_score = min(max((float(item.profit_factor) - 1.0) / 1.0, 0.0), 2.0)
    expectancy_score = max(float(item.expectancy), 0.0)
    winrate_score = max(float(item.winrate) - 0.5, 0.0)

    context_penalty = (
        float(item.risk_context_weak_ratio) * 0.35
        + float(item.lifecycle_problem_ratio) * 0.35
        + max(0.0, 0.5 - float(item.quality_full_ratio)) * 0.20
    )

    heat_penalty = float(item.high_heat_ratio) * 0.10

    raw_score = (
        pf_score * 40.0
        + expectancy_score * 2.0
        + winrate_score * 30.0
        + float(item.quality_full_ratio) * 20.0
    )

    score = max(0.0, raw_score * sample_factor * (1.0 - min(context_penalty + heat_penalty, 0.9)))

    if trades < 20:
        rank_status = "WATCH_LOW_SAMPLE"
        reason = "малая_выборка"
    elif item.status in {"WEAK", "NO_TRADES"}:
        rank_status = "REJECT"
        reason = f"слабая_статистика:{item.status}"
    elif item.risk_context_weak_ratio > 0.25:
        rank_status = "WATCH_CONTEXT_WEAK"
        reason = "слабое_качество_контекста"
    elif item.profit_factor >= 1.3 and item.expectancy > 0 and score >= 25:
        rank_status = "PROMOTE"
        reason = "стратегия_перспективна"
    elif item.profit_factor >= 1.0 and item.expectancy >= 0:
        rank_status = "WATCH"
        reason = "нейтрально_положительная_статистика"
    else:
        rank_status = "REJECT"
        reason = "нет_подтвержденного_преимущества"

    return StrategyRankingDecisionV2(
        symbol=item.symbol,
        strategy=item.strategy,
        timeframe=item.timeframe,
        trade_source=item.trade_source,
        score=round(score, 6),
        rank_status=rank_status,
        reason=reason,
    )
