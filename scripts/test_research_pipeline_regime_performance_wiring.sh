#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/research_pipeline_orchestrator.py \
  src/scripts/analytics/build_strategy_regime_performance.py

grep -q "enrich_trade_context_from_feature_snapshots.py" src/scripts/research_pipeline_orchestrator.py
grep -q "build_strategy_regime_performance.py" src/scripts/research_pipeline_orchestrator.py
grep -q "build_strategy_statistics_v2.py" src/scripts/research_pipeline_orchestrator.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/research_pipeline_orchestrator.py").read_text()

enrich_pos = text.find("enrich_trade_context_from_feature_snapshots.py")
regime_pos = text.find("build_strategy_regime_performance.py")
stats_pos = text.find("build_strategy_statistics_v2.py")

assert enrich_pos != -1
assert regime_pos != -1
assert stats_pos != -1
assert enrich_pos < regime_pos < stats_pos

print("REGIME_PERFORMANCE_AFTER_CONTEXT_BEFORE_STATS_OK")
PY

echo "RESEARCH_PIPELINE_REGIME_PERFORMANCE_WIRING_OK"
