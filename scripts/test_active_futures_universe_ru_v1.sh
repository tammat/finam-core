#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_ACTIVE_FUTURES_UNIVERSE_RU_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

out="/tmp/active_futures_universe_ru_v1.html"
curl -fsS "http://127.0.0.1:8088/active-futures-universe" > "$out"

grep -q "Семейство" "$out"
grep -q "Инструмент" "$out"
grep -q "История" "$out"
grep -q "PF ист." "$out"
grep -q "Средний ист., %" "$out"
grep -q "24ч" "$out"
grep -q "PF 24ч" "$out"
grep -q "Средний 24ч, %" "$out"
grep -q "Последний сигнал" "$out"
grep -q "Обновлено" "$out"
grep -q "🟢 ОК" "$out"
grep -q "🟡 Вторичн." "$out"

if grep -Eq 'Hist completed|Hist PF|Hist expectancy|Live completed|Live PF|Live expectancy|Live last|As of' "$out"; then
  echo "VERDICT=ACTIVE_FUTURES_UNIVERSE_HAS_ENGLISH_HEADERS"
  exit 1
fi

if grep -Eq '20[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?\+00:00' "$out"; then
  echo "VERDICT=ACTIVE_FUTURES_UNIVERSE_HAS_RAW_UTC"
  exit 1
fi

echo "VERDICT=ACTIVE_FUTURES_UNIVERSE_RU_OK"
echo "TEST_ACTIVE_FUTURES_UNIVERSE_RU_V1_OK"
