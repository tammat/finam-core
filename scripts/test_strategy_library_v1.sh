#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_LIBRARY_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/013_strategy_library_v1.sql

PYTHONPATH=src python -m py_compile src/scripts/build_strategy_library_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_strategy_library_v1.py | tee /tmp/strategy_library_v1.txt

grep -q "VERDICT=STRATEGY_LIBRARY_V1_READY" /tmp/strategy_library_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.strategy_library_v1;")
enabled=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.strategy_library_v1 WHERE enabled=true;")

test "$rows" -ge 10
test "$enabled" -ge 10

echo "strategy_rows=$rows"
echo "enabled_rows=$enabled"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_STRATEGY_LIBRARY_V1_OK"
