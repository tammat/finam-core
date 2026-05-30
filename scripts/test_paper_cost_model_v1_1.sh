#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_PAPER_COST_MODEL_V1_1_START"

python -m py_compile \
  src/finam_core/execution/paper_cost_model.py \
  src/finam_core/execution/paper_engine.py

PAPER_CURRENCY=RUB \
PAPER_BROKER_COMMISSION_RATE=0.00108324 \
PAPER_EXCHANGE_COMMISSION_RATE=0.0005 \
PAPER_MIN_COMMISSION=50 \
PAPER_TAX_ENABLED=1 \
PAPER_TAX_RATE=0.15 \
python - <<'PY'
from finam_core.execution.paper_engine import PaperExecutionEngine

engine = PaperExecutionEngine(slippage_coef=0)

fill = engine.execute(
    {
        "symbol": "USDRUBF@RTSX",
        "side": "BUY",
        "qty": 10,
        "tax_base_rub": 1000.0,
    },
    {"bid": 100.0, "ask": 100.0, "timestamp": 1},
)

assert fill.currency == "RUB"
assert fill.price == 100.0
assert fill.qty == 10.0

# notional = 100 * 10 = 1000
# commission raw = 1000 * (0.00108324 + 0.0005) = 1.58324
# min commission = 50
# tax = 1000 * 0.15 = 150
assert abs(fill.commission - 50.0) < 1e-9, fill
assert abs(fill.tax_rub - 150.0) < 1e-9, fill
assert abs(fill.net_cost_rub - 200.0) < 1e-9, fill
assert fill.broker_commission_rub > 0
assert fill.exchange_commission_rub > 0

print("TEST_PAPER_COST_MODEL_V1_1_OK")
PY
