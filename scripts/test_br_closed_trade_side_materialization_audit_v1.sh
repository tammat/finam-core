#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_br_closed_trade_side_materialization_audit_v1.py

python3 src/scripts/analytics/build_br_closed_trade_side_materialization_audit_v1.py \
  | tee /tmp/br_closed_trade_side_materialization_audit_v1.log

grep -q "BR CLOSED TRADE SIDE MATERIALIZATION AUDIT V1" \
  /tmp/br_closed_trade_side_materialization_audit_v1.log

grep -q "TRADE_SIDE_ROWS" \
  /tmp/br_closed_trade_side_materialization_audit_v1.log

grep -q "CLOSED_SIDE_ROWS" \
  /tmp/br_closed_trade_side_materialization_audit_v1.log

grep -q "MATERIALIZATION_SUMMARY" \
  /tmp/br_closed_trade_side_materialization_audit_v1.log

grep -q "BR_CLOSED_TRADE_SIDE_MATERIALIZATION_AUDIT_V1_OK" \
  /tmp/br_closed_trade_side_materialization_audit_v1.log

echo "TEST_BR_CLOSED_TRADE_SIDE_MATERIALIZATION_AUDIT_V1_OK"
