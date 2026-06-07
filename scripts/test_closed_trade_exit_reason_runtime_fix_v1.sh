#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/materialize_closed_trades_from_trades_v1_1.py

grep -q "closed_trade_exit_reason_runtime_fix_v1" \
  src/scripts/analytics/materialize_closed_trades_from_trades_v1_1.py

grep -q '"exit_reason"' \
  src/scripts/analytics/materialize_closed_trades_from_trades_v1_1.py

grep -q '"exit_trade_id"' \
  src/scripts/analytics/materialize_closed_trades_from_trades_v1_1.py

grep -q '"exit_fill_id"' \
  src/scripts/analytics/materialize_closed_trades_from_trades_v1_1.py

echo TEST_CLOSED_TRADE_EXIT_REASON_RUNTIME_FIX_V1_OK
