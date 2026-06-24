#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_ACTIVE_FUTURES_UNIVERSE_GROUP_RENDER_FIX_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

out="/tmp/active_futures_universe_group_render_fix_v1.html"
curl -fsS "http://127.0.0.1:8088/active-futures-universe" > "$out"

grep -q "GDU6@RTSX" "$out"
grep -q "GLU6@RTSX" "$out"
grep -q "BRN6@RTSX" "$out"
grep -q "NGM6@RTSX" "$out"
grep -q "🟢 ОК" "$out"
grep -q "🟡 Вторичн." "$out"

if grep -A20 "🟢 ОК" "$out" | grep -q "Нет данных"; then
  echo "VERDICT=PRIMARY_GROUP_STILL_EMPTY"
  exit 1
fi

if grep -A20 "🟡 Вторичн." "$out" | grep -q "Нет данных"; then
  echo "VERDICT=SECONDARY_GROUP_STILL_EMPTY"
  exit 1
fi

echo "VERDICT=ACTIVE_FUTURES_UNIVERSE_GROUP_RENDER_FIX_OK"
echo "TEST_ACTIVE_FUTURES_UNIVERSE_GROUP_RENDER_FIX_V1_OK"
