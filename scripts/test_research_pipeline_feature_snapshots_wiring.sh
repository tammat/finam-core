#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/research_pipeline_orchestrator.py \
  src/scripts/features/build_market_feature_snapshots.py

grep -q "build_market_feature_snapshots.py" src/scripts/research_pipeline_orchestrator.py
grep -q "build_trade_context_snapshots.py" src/scripts/research_pipeline_orchestrator.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/research_pipeline_orchestrator.py").read_text()

feature_pos = text.find("build_market_feature_snapshots.py")
context_pos = text.find("build_trade_context_snapshots.py")

assert feature_pos != -1
assert context_pos != -1
assert feature_pos < context_pos

print("FEATURE_SNAPSHOTS_BEFORE_TRADE_CONTEXT_OK")
PY

echo "RESEARCH_PIPELINE_FEATURE_SNAPSHOTS_WIRING_OK"
