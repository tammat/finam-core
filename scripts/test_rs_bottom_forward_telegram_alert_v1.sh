#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BOTTOM_FORWARD_TELEGRAM_ALERT_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_rs_bottom_forward_healthcheck_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_rs_bottom_forward_healthcheck_v1.py | tee "$out"

grep -q "TEST_RS_BOTTOM_FORWARD_HEALTHCHECK_V1_OK" "$out"
grep -q "completed_alert_required=" "$out"
grep -q "telegram_alert_sent=" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"

if grep -q "completed_alert_required=0" "$out"; then
  grep -q "telegram_alert_sent=0" "$out"
fi

grep -Eq "VERDICT=(RS_BOTTOM_FORWARD_HEALTHCHECK_READY|RS_BOTTOM_FORWARD_COMPLETED_ALERT_REQUIRED)" "$out"

echo "VERDICT=RS_BOTTOM_FORWARD_TELEGRAM_ALERT_TEST_OK"
echo "TEST_RS_BOTTOM_FORWARD_TELEGRAM_ALERT_V1_OK"
