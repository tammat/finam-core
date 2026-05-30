#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_PAPER_COST_FILL_PERSISTENCE_V1_START"

PAPER_CURRENCY=RUB \
PAPER_BROKER_COMMISSION_RATE=0.00108324 \
PAPER_EXCHANGE_COMMISSION_RATE=0.00050000 \
PAPER_MIN_COMMISSION=50 \
PAPER_TAX_ENABLED=1 \
PAPER_TAX_RATE=0.15 \
python - <<'PY'
import time

from finam_core.execution.paper_engine import PaperExecutionEngine
from finam_core.storage.postgres_logger import PostgresLogger

engine = PaperExecutionEngine(slippage_coef=0.0)

fill = engine.execute(
    {
        "symbol": "TEST_COST@PAPER",
        "side": "BUY",
        "qty": 1,
        "tax_base_rub": 1000.0,
    },
    {
        "bid": 100.0,
        "ask": 100.0,
        "timestamp": time.time(),
    },
)

logger = PostgresLogger()
logger.log_fill(fill, execution_type="paper_cost_test")

print(
    "TEST_COST_FILL",
    f"symbol={fill.symbol}",
    f"qty={fill.qty}",
    f"price={fill.price}",
    f"commission={fill.commission}",
    f"currency={fill.currency}",
    f"broker_commission_rub={fill.broker_commission_rub}",
    f"exchange_commission_rub={fill.exchange_commission_rub}",
    f"tax_rub={fill.tax_rub}",
    f"net_cost_rub={fill.net_cost_rub}",
    flush=True,
)

assert fill.currency == "RUB"
assert abs(fill.commission - 50.0) < 1e-9
assert abs(fill.tax_rub - 150.0) < 1e-9
assert abs(fill.net_cost_rub - 200.0) < 1e-9

print("TEST_PAPER_COST_FILL_PERSISTENCE_V1_OK")
PY
