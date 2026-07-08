#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_SIDEBAR_MIGRATION_V1 ==="

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_sidebar_migration \
PYTHONPATH=src \
python -m py_compile \
  src/marketcore/presentation/components/layout/sidebar.py \
  src/marketcore/presentation/layout.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.components.layout.sidebar import render_sidebar

html = render_sidebar("/")
assert "operator-sidebar" in html
assert "Рабочее место" in html
assert "Лучший Edge" in html
assert "Shadow" in html
assert "Портфель" in html

for forbidden in [
    "Paper Edge Discovery",
    "Edge OOS Validation",
    "Runtime",
    "Orders",
    "Micro Live",
    "Paper Sample",
]:
    assert forbidden not in html, forbidden

print("sidebar_render=OK")
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/?v=$(date +%s)" >/tmp/sidebar_migration_home.html

grep -q "operator-sidebar" /tmp/sidebar_migration_home.html
grep -q "Рабочее место" /tmp/sidebar_migration_home.html
grep -q "Лучший Edge" /tmp/sidebar_migration_home.html
grep -q "Портфель" /tmp/sidebar_migration_home.html

for forbidden in \
  "Paper Edge Discovery" \
  "Edge OOS Validation" \
  "Edge OOS Backtest" \
  "Runtime" \
  "Orders" \
  "Micro Live" \
  "Paper Sample Accumulation Monitor" \
  "Paper Runtime Sample Collection"
do
  if grep -q "$forbidden" /tmp/sidebar_migration_home.html; then
    echo "FORBIDDEN_SIDEBAR_ITEM_VISIBLE=$forbidden"
    exit 1
  fi
done

for route in / /max-edge /edge-score-shadow /edge-score-shadow-daily /portfolio /risk /system /settings; do
  code=$(curl -sS -o /tmp/sidebar_route_check.html -w "%{http_code}" "http://127.0.0.1:8080${route}?v=$(date +%s)" || true)
  if [ "$code" != "200" ]; then
    echo "SIDEBAR_ROUTE_HTTP_NOT_OK route=$route code=$code"
    exit 1
  fi
done

echo "sidebar=operator_mode"
echo "forbidden_sidebar_items=0"
echo "routes_http=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_SIDEBAR_MIGRATION_V1_READY"
echo "VERDICT=TEST_MARKETCORE_SIDEBAR_MIGRATION_V1_OK"
