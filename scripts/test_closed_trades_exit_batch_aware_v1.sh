#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
[[ -x "$PY_BIN" ]] || PY_BIN="$(command -v python3)"

echo "TEST_CLOSED_TRADES_EXIT_BATCH_AWARE_V1_START"

"$PY_BIN" -m py_compile \
  src/scripts/analytics/materialize_closed_trades_from_fills_v1.py \
  src/scripts/analytics/build_ng_runtime_governance_statistics_v1.py

grep -q "exit_batch_size" src/scripts/analytics/materialize_closed_trades_from_fills_v1.py
grep -q "PERFORMANCE_SINGLE_EXIT_TRADES" src/scripts/analytics/build_ng_runtime_governance_statistics_v1.py
grep -q "PERFORMANCE_BATCH_EXIT_TRADES" src/scripts/analytics/build_ng_runtime_governance_statistics_v1.py

"$PY_BIN" src/scripts/analytics/materialize_closed_trades_from_fills_v1.py \
  --symbol NGN6@RTSX \
  --dry-run \
  > /tmp/closed_trades_exit_batch_aware_v1.out

grep -q "SYMBOL_SUMMARY symbol=NGN6@RTSX" /tmp/closed_trades_exit_batch_aware_v1.out

echo "TEST_CLOSED_TRADES_EXIT_BATCH_AWARE_V1_OK"
