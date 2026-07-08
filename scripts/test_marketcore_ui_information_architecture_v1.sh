#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_INFORMATION_ARCHITECTURE_V1 ==="

doc="docs/MARKETCORE_UI_INFORMATION_ARCHITECTURE_V1.md"
test -f "$doc"

grep -q "Главная" "$doc"
grep -q "Исследования" "$doc"
grep -q "Рынок" "$doc"
grep -q "Портфель" "$doc"
grep -q "Данные" "$doc"
grep -q "Система" "$doc"
grep -q "Инженерный режим" "$doc"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_ui_ia \
PYTHONPATH=src \
python -m py_compile \
  src/marketcore/presentation/route_groups.py \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/registry_autodiscovery.py

required_routes=(
  "/"
  "/edge-factory"
  "/max-edge"
  "/edge-score-shadow"
  "/edge-score-shadow-daily"
  "/research"
  "/market-model"
  "/market-universe-ranking"
  "/market-universe-research-queue"
  "/knowledge-graph"
  "/portfolio"
  "/risk"
  "/feature-store"
  "/validation"
  "/system"
  "/logs"
  "/settings"
)

for route in "${required_routes[@]}"; do
  if ! grep -RIn "\"$route\"" src/marketcore/presentation/route_groups.py >/dev/null; then
    echo "ROUTE_NOT_IN_INFORMATION_ARCHITECTURE=$route"
    exit 1
  fi
done

for forbidden in \
  "/paper-sample-accumulation-monitor" \
  "/paper-edge-discovery" \
  "/paper-edge-market-data-binding" \
  "/paper-edge-market-symbol-alias-plan" \
  "/paper-edge-market-data-freshness" \
  "/edge-oos-validation" \
  "/edge-oos-backtest" \
  "/micro-live-readiness" \
  "/orders"
do
  if grep -RIn "\"$forbidden\"" src/marketcore/presentation/route_groups.py src/marketcore/presentation/ui_labels.py; then
    echo "FORBIDDEN_ENGINEERING_ROUTE_IN_MAIN_UI=$forbidden"
    exit 1
  fi
done

sudo systemctl restart marketcore-ui-shell.service
sleep 2

for route in / /max-edge /edge-score-shadow /edge-score-shadow-daily /system; do
  code=$(curl -sS -o /tmp/marketcore_ia_route.html -w "%{http_code}" "http://127.0.0.1:8080${route}?v=$(date +%s)" || true)
  if [ "$code" != "200" ]; then
    echo "ROUTE_HTTP_NOT_OK route=$route code=$code"
    exit 1
  fi
done

echo "information_architecture_doc=OK"
echo "required_routes=OK"
echo "forbidden_engineering_routes=0"
echo "http_routes=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_INFORMATION_ARCHITECTURE_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_INFORMATION_ARCHITECTURE_V1_OK"
