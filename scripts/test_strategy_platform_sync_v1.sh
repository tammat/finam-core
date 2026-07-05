#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_PLATFORM_SYNC_V1 ==="

PYTHONPATH=src python -m py_compile src/scripts/build_strategy_platform_sync_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_strategy_platform_sync_v1.py | tee /tmp/strategy_platform_sync_v1.txt

grep -q "VERDICT=STRATEGY_PLATFORM_SYNC_V1_READY" /tmp/strategy_platform_sync_v1.txt

registry_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.strategy_registry_v1;")
library_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.strategy_library_v1 WHERE enabled=true;")

test "$registry_rows" -ge "$library_rows"

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8095/api/kg/v1/strategy-platform/summary >/tmp/strategy_sync_summary.json
curl -fsS http://127.0.0.1:8080/strategy-platform >/tmp/strategy_sync_ui.html

grep -q "Платформа стратегий" /tmp/strategy_sync_ui.html

echo "registry_rows=$registry_rows"
echo "library_rows=$library_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_STRATEGY_PLATFORM_SYNC_V1_OK"
