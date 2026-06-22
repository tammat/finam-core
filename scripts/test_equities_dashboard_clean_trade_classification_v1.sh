#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITIES_DASHBOARD_CLEAN_TRADE_CLASSIFICATION_V1 ==="

html="$(curl -fsS http://127.0.0.1:8088/equities)"

echo "$html" | grep -q "Классификация сделок"
echo "$html" | grep -q "Чистые runtime сделки"
echo "$html" | grep -q "Legacy/Fallback сделки"
echo "$html" | grep -q "не используются для оценки edge"

if echo "$html" | grep -qi "Traceback\|ModuleNotFoundError\|raw_json\|<pre>{"; then
  echo "DIRTY_OUTPUT_FOUND=1"
  exit 1
fi

echo "VERDICT=EQUITIES_DASHBOARD_CLEAN_TRADE_CLASSIFICATION_OK"
echo "TEST_EQUITIES_DASHBOARD_CLEAN_TRADE_CLASSIFICATION_V1_OK"
