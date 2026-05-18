from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class RuntimeGovernanceResult:
    trade_date: date
    scorecards_saved: int
    rank_decisions_saved: int
    cooldowns_saved: int
    allocation_count: int


class RuntimeGovernanceCoordinator:
    """
    Русский комментарий: единый coordinator adaptive runtime governance.

    Последовательность:
    1. scorecard по closed_trades;
    2. rank decisions;
    3. cooldown rules;
    4. runtime universe allocation.
    """

    def __init__(
        self,
        *,
        scorecard_persistence: Any,
        rank_persistence: Any,
        cooldown_builder: Any,
        allocator: Any,
    ) -> None:
        self.scorecard_persistence = scorecard_persistence
        self.rank_persistence = rank_persistence
        self.cooldown_builder = cooldown_builder
        self.allocator = allocator

    def run_daily(
        self,
        *,
        trade_date: date,
        max_symbols: int = 5,
        min_score: float = 0.35,
    ) -> RuntimeGovernanceResult:
        scorecards_saved = self.scorecard_persistence.calculate_and_save_daily(trade_date)
        rank_decisions_saved = self.rank_persistence.calculate_and_save_daily(trade_date)
        cooldowns_saved = self.cooldown_builder.build(trade_date)

        allocation_count = self.allocator.allocate(
            max_symbols=max_symbols,
            min_score=min_score,
        )

        result = RuntimeGovernanceResult(
            trade_date=trade_date,
            scorecards_saved=int(scorecards_saved or 0),
            rank_decisions_saved=int(rank_decisions_saved or 0),
            cooldowns_saved=int(cooldowns_saved or 0),
            allocation_count=int(allocation_count or 0),
        )

        print(
            "RUNTIME_GOVERNANCE_OK "
            f"date={result.trade_date} "
            f"scorecards={result.scorecards_saved} "
            f"rank_decisions={result.rank_decisions_saved} "
            f"cooldowns={result.cooldowns_saved} "
            f"allocated={result.allocation_count}",
            flush=True,
        )

        return result
