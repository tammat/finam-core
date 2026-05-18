#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/runtime_governance_coordinator.py

python - <<'PY'
from datetime import date

from finam_core.runtime.runtime_governance_coordinator import (
    RuntimeGovernanceCoordinator,
)


class ScorecardPersistence:
    def calculate_and_save_daily(self, trade_date):
        return 2


class RankPersistence:
    def calculate_and_save_daily(self, trade_date):
        return 2


class CooldownBuilder:
    def build(self, trade_date):
        return 1


class Allocator:
    def allocate(self, *, max_symbols, min_score):
        assert max_symbols == 3
        assert min_score == 0.5
        return 2


coordinator = RuntimeGovernanceCoordinator(
    scorecard_persistence=ScorecardPersistence(),
    rank_persistence=RankPersistence(),
    cooldown_builder=CooldownBuilder(),
    allocator=Allocator(),
)

result = coordinator.run_daily(
    trade_date=date(2026, 5, 15),
    max_symbols=3,
    min_score=0.5,
)

assert result.scorecards_saved == 2
assert result.rank_decisions_saved == 2
assert result.cooldowns_saved == 1
assert result.allocation_count == 2

print("OK: runtime governance coordinator")
PY
