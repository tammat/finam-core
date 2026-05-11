#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f src/finam_core/risk/real_stock_safety_gate.py

grep -q "REAL_STOCKS_ONLY" src/finam_core/risk/real_stock_safety_gate.py
grep -q "REAL_STOCK_GATE_BLOCKED_FUTURES" src/finam_core/risk/real_stock_safety_gate.py
grep -q "REAL_STOCK_GATE_ALLOWED_MISX_STOCK" src/finam_core/risk/real_stock_safety_gate.py

PYTHONPATH=src REAL_STOCKS_ONLY=1 python - <<'PY'
from finam_core.risk.real_stock_safety_gate import RealStockSafetyGate

gate = RealStockSafetyGate()

assert gate.check("SBER@MISX", execution_mode="real").allowed is True
assert gate.check("BRM6@RTSX", execution_mode="real").allowed is False
assert gate.check("NGM6@RTSX", execution_mode="real").reason == "REAL_STOCK_GATE_BLOCKED_FUTURES"
assert gate.check("BRM6@RTSX", execution_mode="paper").allowed is True

print("REAL_STOCK_SAFETY_GATE_RUNTIME_OK")
PY

python -m py_compile src/finam_core/risk/real_stock_safety_gate.py
python -m py_compile src/scripts/run_market_pipeline.py

echo "REAL_STOCK_SAFETY_GATE_TEST_OK"
