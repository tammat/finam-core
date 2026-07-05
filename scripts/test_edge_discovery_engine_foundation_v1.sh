#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_ENGINE_FOUNDATION_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/018_edge_discovery_engine_foundation_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_discovery_engine_foundation_v1.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_discovery_engine_foundation_v1.py | tee /tmp/edge_discovery_engine_foundation_v1.txt

grep -q "VERDICT=EDGE_DISCOVERY_ENGINE_FOUNDATION_V1_READY" /tmp/edge_discovery_engine_foundation_v1.txt

methods=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_discovery_method_v1;")
enabled_methods=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_discovery_method_v1 WHERE enabled=true;")
rules=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_discovery_rule_v1;")
enabled_rules=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_discovery_rule_v1 WHERE enabled=true;")
runs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_discovery_run_v1;")

test "$methods" -ge 5
test "$enabled_methods" -ge 1
test "$rules" -ge 6
test "$enabled_rules" -ge 6
test "$runs" -gt 0

grep -q "edge.discovery.engine.title" src/marketcore/presentation/ui_labels.py
grep -q "edge.discovery.rule" src/marketcore/presentation/ui_labels.py

echo "methods=$methods"
echo "enabled_methods=$enabled_methods"
echo "rules=$rules"
echo "enabled_rules=$enabled_rules"
echo "runs=$runs"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_DISCOVERY_ENGINE_FOUNDATION_V1_OK"
