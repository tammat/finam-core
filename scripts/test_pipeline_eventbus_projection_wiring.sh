#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/run_market_pipeline.py").read_text(encoding="utf-8")

assert "EventProjectionBridge" in text
assert "RealtimeProjectionSubscriber" in text
assert "ENABLE_REALTIME_PROJECTIONS" in text
assert "PIPE_PROJECTION_BRIDGE_OK" in text
assert "PIPE_PROJECTION_BRIDGE_FAILED" in text
assert "projection_bridge.attach()" in text

print("PIPELINE_EVENTBUS_PROJECTION_WIRING_OK")
PY
