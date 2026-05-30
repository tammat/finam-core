#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_PAPER_COST_MODEL_V1_START"

python -m py_compile \
  src/finam_core/execution/paper_cost_model.py \
  src/finam_core/execution/paper_engine.py

PAPER_BROKER_COMMISSION_RATE=0.0004 \
PAPER_EXCHANGE_COMMISSION_RATE=0.0001 \
PAPER_MIN_COMMISSION=0 \
python - <<'PY'
from finam_core.execution.paper_engine import PaperExecutionEngine

engine = PaperExecutionEngine(slippage_coef=0)
fill = engine.execute(
    {"symbol": "USDRUBF@RTSX", "side": "BUY", "qty": 10},
    {"bid": 100.0, "ask": 100.0, "timestamp": 1},
)

expected = 100.0 * 10 * (0.0004 + 0.0001)

assert fill.symbol == "USDRUBF@RTSX"
assert fill.qty == 10.0
assert fill.price == 100.0
assert abs(fill.commission - expected) < 1e-9, (fill.commission, expected)

print("TEST_PAPER_COST_MODEL_V1_OK")
PY
