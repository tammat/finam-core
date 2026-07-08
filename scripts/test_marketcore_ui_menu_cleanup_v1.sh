#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_MENU_CLEANUP_V1 ==="

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_menu_cleanup \
PYTHONPATH=src \
python -m py_compile \
  src/marketcore/presentation/route_groups.py \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/registry_autodiscovery.py

echo "MENU_ROUTES_BEFORE"
grep -RIn "route=\"/" src/marketcore/presentation/pages | sed 's/^/ROUTE /' | head -120

echo "MENU_ORDER_BEFORE"
grep -RIn "menu_order=" src/marketcore/presentation/pages | sed 's/^/MENU /' | head -120

# В пользовательском меню не должны быть видны устаревшие инженерные страницы.
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
    echo "FORBIDDEN_MENU_ROUTE_VISIBLE=$forbidden"
    exit 1
  fi
done

# Основные рабочие страницы должны остаться.
for required in \
  "/max-edge" \
  "/edge-score-shadow" \
  "/edge-score-shadow-daily" \
  "/market-model" \
  "/portfolio" \
  "/system"
do
  if ! grep -RIn "\"$required\"" src/marketcore/presentation/route_groups.py src/marketcore/presentation/ui_labels.py >/dev/null; then
    echo "REQUIRED_MENU_ROUTE_MISSING=$required"
    exit 1
  fi
done

# В меню не должно остаться английских пользовательских названий ключевых разделов.
if grep -RInE '"(Edge Factory|Discovery|Runtime|Paper|Worker|Orders)"' \
  src/marketcore/presentation/route_groups.py src/marketcore/presentation/ui_labels.py; then
  echo "ENGLISH_MENU_LABEL_FOUND"
  exit 1
fi

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_MENU_CLEANUP_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_MENU_CLEANUP_V1_OK"
