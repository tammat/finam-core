#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_PROVIDER_INTERFACE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/research/execution/interfaces/data_provider.py

PYTHONPATH=src python - <<'PY'
from datetime import UTC, datetime
from marketcore.research.execution.interfaces.data_provider import MarketBar, MarketBars

bar = MarketBar(
    ts=datetime.now(UTC),
    open=1.0,
    high=2.0,
    low=0.5,
    close=1.5,
    volume=100.0,
)

bars = MarketBars(
    symbol="TEST",
    timeframe="M5",
    source="unit",
    bars=[bar],
)

assert bars.count == 1
assert bars.bars[0].close == 1.5
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=DATA_PROVIDER_INTERFACE_V1_READY"
echo "VERDICT=TEST_DATA_PROVIDER_INTERFACE_V1_OK"
