#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_DASHBOARD_SINGLE_SOURCE_OF_TRUTH_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

out="/tmp/dashboard_single_source_of_truth_v1.html"
curl -fsS "http://127.0.0.1:8088/active-futures-universe" > "$out"

grep -q "Источник статуса:</b> live 24h" "$out"
grep -q "история показана справочно" "$out"

# По текущим данным GDU6/GLU6 не должны оставаться в ОК,
# потому что live expectancy отрицательная.
if grep -A15 "🟢 ОК" "$out" | grep -Eq "GDU6@RTSX|GLU6@RTSX"; then
  echo "VERDICT=STALE_HISTORY_STATUS_STILL_USED"
  exit 1
fi

echo "VERDICT=DASHBOARD_SINGLE_SOURCE_OF_TRUTH_OK"
echo "TEST_DASHBOARD_SINGLE_SOURCE_OF_TRUTH_V1_OK"
