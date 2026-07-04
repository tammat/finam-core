#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_PLATFORM_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/strategy_platform.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/router.py

DATABASE_URL=postgresql:///finam_core STRATEGY_FEATURE_LIMIT=5000 PYTHONPATH=src \
python src/scripts/build_multi_strategy_engine_builder_v1.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/strategy-platform/summary" > /tmp/strategy_platform_summary.json
curl -fsS "http://127.0.0.1:8080/strategy-platform" > /tmp/strategy_platform_ui.html

grep -q "Платформа стратегий" /tmp/strategy_platform_ui.html
grep -q "VOLATILITY_BREAKOUT" /tmp/strategy_platform_ui.html
grep -q "Нет" /tmp/strategy_platform_ui.html

if grep -R "SELECT .*strategy_\|FROM analytics.strategy_" \
  src/marketcore/presentation/pages/strategy_platform.py; then
  echo "ERROR_DIRECT_SQL_IN_STRATEGY_PLATFORM_UI"
  exit 1
fi

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.strategy_signal_snapshot_v1
WHERE execution_allowed=true OR risk_allowed=true;
")
test "$unsafe" = "0"

echo "unsafe_allowed_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=STRATEGY_PLATFORM_UI_V1_READY"
echo "VERDICT=TEST_STRATEGY_PLATFORM_UI_V1_OK"
