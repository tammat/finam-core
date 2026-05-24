#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/research_pipeline_orchestrator.py \
  src/scripts/features/enrich_trade_context_from_feature_snapshots.py

grep -q "build_trade_context_snapshots.py" src/scripts/research_pipeline_orchestrator.py
grep -q "enrich_trade_context_from_feature_snapshots.py" src/scripts/research_pipeline_orchestrator.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/research_pipeline_orchestrator.py").read_text()

context_pos = text.find("build_trade_context_snapshots.py")
enrich_pos = text.find("enrich_trade_context_from_feature_snapshots.py")

assert context_pos != -1
assert enrich_pos != -1
assert context_pos < enrich_pos

print("TRADE_CONTEXT_FEATURE_ENRICHMENT_AFTER_CONTEXT_OK")
PY

echo "RESEARCH_PIPELINE_TRADE_CONTEXT_FEATURE_ENRICHMENT_WIRING_OK"
