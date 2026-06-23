#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITIES_DASHBOARD_NO_TRADING_STATUS_V1 ==="

html="$(curl -fsS http://127.0.0.1:8088/equities)"

echo "$html" | grep -q "Реальная торговля"
echo "$html" | grep -q "запрещена"
echo "$html" | grep -q "Исполнение"
echo "$html" | grep -q "отключено"
echo "$html" | grep -q "торговля по акциям не ведётся"
echo "$html" | grep -q "legacy-сделок не означает, что сейчас идёт торговля"

echo "VERDICT=EQUITIES_DASHBOARD_NO_TRADING_STATUS_OK"
echo "TEST_EQUITIES_DASHBOARD_NO_TRADING_STATUS_V1_OK"
