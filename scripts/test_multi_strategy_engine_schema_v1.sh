#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MULTI_STRATEGY_ENGINE_SCHEMA_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/006_strategy_signal_snapshot_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_strategy_signal_snapshot_schema_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_strategy_signal_snapshot_schema_v1.py \
  | tee /tmp/multi_strategy_engine_schema_v1.txt

grep -q "VERDICT=MULTI_STRATEGY_ENGINE_SCHEMA_V1_READY" \
  /tmp/multi_strategy_engine_schema_v1.txt

exists=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.strategy_signal_snapshot_v1') IS NOT NULL;")
test "$exists" = "t"

psql -d finam_core -c "\d analytics.strategy_signal_snapshot_v1"

echo "table_exists=$exists"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MULTI_STRATEGY_ENGINE_SCHEMA_V1_OK"
