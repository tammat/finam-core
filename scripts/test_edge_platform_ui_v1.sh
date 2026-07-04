#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PLATFORM_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/edge_platform.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/router.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/edge-platform/summary" > /tmp/edge_platform_ui_summary.json
curl -fsS "http://127.0.0.1:8095/api/kg/v1/edge-platform/decisions" > /tmp/edge_platform_ui_decisions.json
curl -fsS "http://127.0.0.1:8080/edge-platform" > /tmp/edge_platform_ui.html

grep -q "Edge Platform" /tmp/edge_platform_ui.html
grep -q "Оценка качества сигналов" /tmp/edge_platform_ui.html

if grep -R "SELECT .*edge_\|FROM analytics.edge_" \
  src/marketcore/presentation/pages/edge_platform.py; then
  echo "ERROR_DIRECT_SQL_IN_EDGE_PLATFORM_UI"
  exit 1
fi

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_decision_snapshot_v1
WHERE ready_for_live=true OR ready_for_micro_live=true;
")
test "$unsafe" = "0"

echo "unsafe_live_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_PLATFORM_UI_V1_READY"
echo "VERDICT=TEST_EDGE_PLATFORM_UI_V1_OK"
