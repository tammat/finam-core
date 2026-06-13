#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_trade_outlier_audit_v1.py

python3 src/scripts/research/build_trade_outlier_audit_v1.py | \
tee /tmp/trade_outlier_audit_v1.log

grep -q "TRADE OUTLIER AUDIT V1" \
  /tmp/trade_outlier_audit_v1.log

grep -Eq \
"VERDICT=OK|VERDICT=INSUFFICIENT_DATA" \
  /tmp/trade_outlier_audit_v1.log

echo TRADE_OUTLIER_AUDIT_V1_OK
