#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
FILE="scripts/research/build_postgresql_edge_parameter_search_v1.py"

cd "$ROOT"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$FILE"

grep -Fq \
  "from finam_core.research.postgresql_edge_backtest_adapter_v1 import (" \
  "$FILE"

grep -Fq \
  "SUPPORTED_STRATEGIES," \
  "$FILE"

grep -Fq \
  "if task.strategy_code not in SUPPORTED_STRATEGIES:" \
  "$FILE"

grep -Fq \
  "reason=UNSUPPORTED_STRATEGY" \
  "$FILE"

PYTHONPATH=src \
"$PYTHON" - <<'PY'
from __future__ import annotations

from finam_core.research.postgresql_edge_backtest_adapter_v1 import (
    SUPPORTED_STRATEGIES,
)


print(
    "supported_strategies="
    + ",".join(sorted(SUPPORTED_STRATEGIES))
)

assert "RSI_MEAN_REVERSION_V1" not in SUPPORTED_STRATEGIES
assert "ATR_IMPULSE_V1" in SUPPORTED_STRATEGIES
assert "MOMENTUM_CONTINUATION_V1" in SUPPORTED_STRATEGIES

print("rsi_rejected=1")
print("atr_supported=1")
print("momentum_supported=1")
print("db_writes_performed=0")
print(
    "VERDICT="
    "POSTGRESQL_EDGE_PARAMETER_SEARCH_PREFLIGHT_STRATEGY_RUNTIME_OK"
)
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_POSTGRESQL_EDGE_PARAMETER_SEARCH_PREFLIGHT_STRATEGY_V1_OK"
