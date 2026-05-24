#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/research_verdict_repository.py \
  src/scripts/research/build_strategy_research_verdict.py

python - <<'PY'
from finam_core.research.research_verdict_repository import StrategyResearchVerdictRepository

repo = StrategyResearchVerdictRepository(database_url="")

verdict, confidence, reason = repo._decide(
    performance_status="WEAK",
    walkforward_status="OOS_CONFIRMED",
    regime_status="WATCH_CONTEXT",
    performance_pf=0.92,
    walkforward_test_pf=1.30,
    regime_pf=1.15,
    performance_expectancy=-0.1,
    walkforward_test_expectancy=0.2,
    regime_expectancy=0.1,
    trades=104,
    oos_trades=32,
)

assert verdict == "WATCH_DIVERGENCE"
assert confidence == 0.45
assert "aggregate" in reason

print("STRATEGY_RESEARCH_VERDICT_UNIT_OK")
PY

grep -q "strategy_performance" src/finam_core/research/research_verdict_repository.py
grep -q "strategy_walkforward_results" src/finam_core/research/research_verdict_repository.py
grep -q "strategy_regime_performance" src/finam_core/research/research_verdict_repository.py
grep -q "STRATEGY_RESEARCH_VERDICT_BUILD_OK" src/scripts/research/build_strategy_research_verdict.py
grep -q "strategy_research_verdicts" scripts/migrate_strategy_research_verdicts_v1.sh

echo "STRATEGY_RESEARCH_VERDICT_REPOSITORY_TEST_OK"
