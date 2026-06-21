#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BOTTOM_FORWARD_ALERT_WHEN_COMPLETED_V1 ==="

out="$(mktemp)"

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_rs_bottom_forward_healthcheck_v1.py | tee "$out"

grep -q "TEST_RS_BOTTOM_FORWARD_HEALTHCHECK_V1_OK" "$out"
grep -q "completed_alert_required=" "$out"
grep -Eq "VERDICT=(RS_BOTTOM_FORWARD_HEALTHCHECK_READY|RS_BOTTOM_FORWARD_COMPLETED_ALERT_REQUIRED)" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"

echo "VERDICT=RS_BOTTOM_FORWARD_ALERT_WHEN_COMPLETED_TEST_OK"
echo "TEST_RS_BOTTOM_FORWARD_ALERT_WHEN_COMPLETED_V1_OK"
