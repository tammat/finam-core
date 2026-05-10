#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/run_market_pipeline.py").read_text(encoding="utf-8")

assert "EventStoreFactory" in text
assert "EventStoreFactory.configure(event_bus=bus)" in text
assert "PIPE_EVENT_STORE_FACTORY_BUS_OK" in text
assert "PIPE_EVENT_STORE_FACTORY_BUS_FAILED" in text

print("PIPELINE_EVENT_STORE_FACTORY_WIRING_OK")
PY
