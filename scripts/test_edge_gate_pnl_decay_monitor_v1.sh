#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_EDGE_GATE_PNL_DECAY_MONITOR_V1_START"

python -m py_compile \
  src/finam_core/analytics/edge_gate_pnl_decay_monitor_v1.py \
  src/scripts/analytics/build_edge_gate_pnl_decay_monitor_v1.py

python - <<'PY'
from finam_core.analytics.edge_gate_pnl_decay_monitor_v1 import (
    EdgeGatePnlDecayMonitorV1,
)

monitor = EdgeGatePnlDecayMonitorV1()

healthy = monitor.evaluate(
    symbol="BR_ROLLING@RTSX",
    side="BUY",
    hour_msk=8,
    expectancy_points=0.218,
    pnl_points=84.11,
    closed_trades=46,
)

decay = monitor.evaluate(
    symbol="BR_ROLLING@RTSX",
    side="BUY",
    hour_msk=19,
    expectancy_points=-0.0486,
    pnl_points=-92.75,
    closed_trades=86,
)

print(
    "DECAY_HEALTHY",
    healthy.enabled,
    healthy.reason,
)

print(
    "DECAY_NEGATIVE",
    decay.enabled,
    decay.reason,
)

assert healthy.enabled is True
assert decay.enabled is False

print("EDGE_GATE_DECAY_MONITOR_RUNTIME_OK")
PY

python src/scripts/analytics/build_edge_gate_pnl_decay_monitor_v1.py

echo "TEST_EDGE_GATE_PNL_DECAY_MONITOR_V1_OK"
