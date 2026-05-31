#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_NG_LIVE_ROUTE_REACHES_MTF_V1_START"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_NG_TICK_ROUTE_NO_INTENT_CONTINUE_MTF" src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

s = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()

start = s.index("# === NG STRATEGY ROUTE")
end = s.index("# === SIMULATION MOVE", start)
block = s[start:end]

assert "\n                return\n" not in block, "NG live route still has early return before MTF aggregation"
assert "CONTINUE_MTF" in block

print("NG_ROUTE_NO_EARLY_RETURN_OK")
PY

echo "TEST_NG_LIVE_ROUTE_REACHES_MTF_V1_OK"
