#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MOBILE_SECTION_SPLIT_V1 ==="

html="$(curl -fsS http://127.0.0.1:8088/mobile)"

echo "$html" | grep -q "Монитор пробоя"
echo "$html" | grep -q "Исследование преимущества"
echo "$html" | grep -q "Состояние системы"
echo "$html" | grep -q "/edge"
echo "$html" | grep -q "/rs-bottom-forward"
echo "$html" | grep -q "/brent-rollover-edge"

if echo "$html" | grep -qi "Traceback\|ModuleNotFoundError\|raw_json\|<pre>{"; then
  echo "MOBILE_DIRTY_TECH_OUTPUT_FOUND=1"
  exit 1
fi

echo "VERDICT=MOBILE_SECTION_SPLIT_OK"
echo "TEST_MOBILE_SECTION_SPLIT_V1_OK"
