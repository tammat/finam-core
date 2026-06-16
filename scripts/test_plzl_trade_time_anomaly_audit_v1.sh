#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_plzl_trade_time_anomaly_audit_v1.py

python3 src/scripts/research/build_plzl_trade_time_anomaly_audit_v1.py \
  | tee /tmp/plzl_trade_time_anomaly_audit_v1.log

grep -q "PLZL TRADE TIME ANOMALY AUDIT V1" /tmp/plzl_trade_time_anomaly_audit_v1.log
grep -q "execution_enabled=0" /tmp/plzl_trade_time_anomaly_audit_v1.log
grep -q "PLZL_TIME_AUDIT_ROW" /tmp/plzl_trade_time_anomaly_audit_v1.log
grep -q "PLZL_TRADE_TIME_ANOMALY_AUDIT_SUMMARY" /tmp/plzl_trade_time_anomaly_audit_v1.log
grep -q "PLZL_TRADE_TIME_ANOMALY_AUDIT_V1_OK" /tmp/plzl_trade_time_anomaly_audit_v1.log

echo TEST_PLZL_TRADE_TIME_ANOMALY_AUDIT_V1_OK
