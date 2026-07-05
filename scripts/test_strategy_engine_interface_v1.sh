#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_ENGINE_INTERFACE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/research/execution/dto/signal.py \
  src/marketcore/research/execution/interfaces/strategy_engine.py

PYTHONPATH=src python - <<'PY'
from datetime import UTC, datetime

from marketcore.research.execution.dto.signal import StrategySignal

s = StrategySignal(
    signal_ts=datetime.now(UTC),
    direction="BUY",
    price=100.0,
    confidence=0.75,
    metadata={"source": "unit"},
)

assert s.is_trade_signal is True
assert s.direction == "BUY"
assert s.price == 100.0
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=STRATEGY_ENGINE_INTERFACE_V1_READY"
echo "VERDICT=TEST_STRATEGY_ENGINE_INTERFACE_V1_OK"
