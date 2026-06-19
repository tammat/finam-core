#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET BREAKOUT READY EVENT DELIVERY TIMER RUNTIME VALIDATION V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "telegram_real_send=0"
echo "orders_create=0"
echo "execution_intents_create=0"

systemctl is-enabled finam-multi-asset-ready-event-delivery.timer >/tmp/ready_delivery_timer_enabled.txt
systemctl is-active finam-multi-asset-ready-event-delivery.timer >/tmp/ready_delivery_timer_active.txt

timer_enabled="$(cat /tmp/ready_delivery_timer_enabled.txt)"
timer_active="$(cat /tmp/ready_delivery_timer_active.txt)"

journalctl -u finam-multi-asset-ready-event-delivery.service --since "30 minutes ago" --no-pager \
  >/tmp/ready_delivery_timer_runtime_validation_v1.log || true

grep -q "MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_V1_OK" /tmp/ready_delivery_timer_runtime_validation_v1.log
grep -q "execution_enabled=0" /tmp/ready_delivery_timer_runtime_validation_v1.log
grep -q "real_trading_enabled=0" /tmp/ready_delivery_timer_runtime_validation_v1.log
grep -q "orders_create=0" /tmp/ready_delivery_timer_runtime_validation_v1.log
grep -q "execution_intents_create=0" /tmp/ready_delivery_timer_runtime_validation_v1.log
grep -q "VERDICT=" /tmp/ready_delivery_timer_runtime_validation_v1.log

if grep -E "Traceback|ERROR|real_trading_enabled=1|execution_enabled=1" /tmp/ready_delivery_timer_runtime_validation_v1.log; then
  echo "VERDICT=MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_TIMER_RUNTIME_VALIDATION_FAILED"
  exit 1
fi

api="$(curl -fsS http://127.0.0.1:8088/api/current)"

echo "$api" >/tmp/ready_delivery_timer_runtime_validation_api_v1.json

grep -q '"execution_enabled": "0"' /tmp/ready_delivery_timer_runtime_validation_api_v1.json
grep -q '"real_trading_enabled": "0"' /tmp/ready_delivery_timer_runtime_validation_api_v1.json
grep -q '"ready_delivery"' /tmp/ready_delivery_timer_runtime_validation_api_v1.json
grep -q '"undelivered_ready": 0' /tmp/ready_delivery_timer_runtime_validation_api_v1.json

echo "timer_enabled=${timer_enabled}"
echo "timer_active=${timer_active}"

grep -E "ready_total=|undelivered_before=|delivery_total=|dry_run_total=|VERDICT=" \
  /tmp/ready_delivery_timer_runtime_validation_v1.log | tail -20

grep -E '"ready_delivery"|"ready_total"|"delivery_total"|"dry_run_total"|"undelivered_ready"|"execution_enabled"|"real_trading_enabled"' \
  /tmp/ready_delivery_timer_runtime_validation_api_v1.json

echo "VERDICT=MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_TIMER_RUNTIME_VALIDATION_OK"
echo TEST_MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_TIMER_RUNTIME_VALIDATION_V1_OK
