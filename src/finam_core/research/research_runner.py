from __future__ import annotations

import uuid
from collections import defaultdict

from finam_core.research.research_repository import ResearchRepository
from finam_core.research.strategy_metrics import calculate_strategy_metrics


def classify_strategy(metrics) -> tuple[str, str]:
    """Русский комментарий: первичная research-классификация стратегии."""

    if metrics.trades < 30:
        return "REJECT", "Недостаточно сделок для оценки"

    if metrics.expectancy <= 0:
        return "REJECT", "Математическое ожидание не подтверждено"

    if metrics.profit_factor < 1.1:
        return "REJECT", "Profit factor ниже минимального research-порога"

    if metrics.max_drawdown < -10000:
        return "REJECT", "Просадка превышает research-лимит"

    return "ACCEPT", "Стратегия прошла первичный research-отбор"


def run_research_layer_v1() -> str:
    repo = ResearchRepository()
    samples = repo.load_trade_samples()

    run_id = f"research_v1_{uuid.uuid4().hex[:12]}"

    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)

    for sample in samples:
        grouped[(sample.strategy, sample.symbol, sample.regime)].append(sample.pnl)

    for (strategy, symbol, regime), pnls in grouped.items():
        metrics = calculate_strategy_metrics(pnls)
        decision, reason = classify_strategy(metrics)

        repo.save_research_result(
            run_id=run_id,
            strategy=strategy,
            symbol=symbol,
            regime=regime,
            metrics=metrics,
            decision=decision,
            reason=reason,
        )

        print(
            "RESEARCH_RESULT "
            f"run_id={run_id} "
            f"strategy={strategy} "
            f"symbol={symbol} "
            f"regime={regime} "
            f"trades={metrics.trades} "
            f"expectancy={metrics.expectancy} "
            f"profit_factor={metrics.profit_factor} "
            f"max_drawdown={metrics.max_drawdown} "
            f"decision={decision} "
            f"reason={reason}",
            flush=True,
        )

    print(f"RESEARCH_LAYER_V1_DONE run_id={run_id} groups={len(grouped)}")
    return run_id


if __name__ == "__main__":
    run_research_layer_v1()
