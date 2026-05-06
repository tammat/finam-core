#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.session.session_manager import SessionManager

sm = SessionManager()

stock = sm.get_regime("SVETP@MISX")
forts = sm.get_regime("BRM6@RTSX")

assert isinstance(stock, dict), stock
assert isinstance(forts, dict), forts
assert "phase" in stock
assert "phase" in forts
assert "allow_entries" in stock
assert "allow_entries" in forts

print("SESSION_ROUTING_OK")
print("STOCK_SESSION", stock)
print("FORTS_SESSION", forts)
PY

grep -q "get_regime(sym)" src/finam_core/pipelines/paper_pipeline.py

echo "PIPELINE_SESSION_SYMBOL_OK"
