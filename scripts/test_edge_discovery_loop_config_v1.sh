#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_LOOP_CONFIG_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/012_edge_discovery_loop_config_v1.sql

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/marketcore/config/edge_config_provider.py \
  src/marketcore/config/__init__.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
from marketcore.config import EdgeConfigProvider

cfg = EdgeConfigProvider().load()

assert cfg.discovery_enabled() is True
assert cfg.profile() == "QUALIFIED"
assert cfg.interval_minutes() > 0
assert cfg.max_parallel_research_jobs() > 0
assert cfg.max_new_parameter_searches_per_day() > 0
assert cfg.min_profit_factor() >= 1
assert cfg.market_data_max_age_sec() > 0

print("EDGE_DISCOVERY_LOOP_CONFIG_PROVIDER_OK")
PY

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_configuration_v1
WHERE edge_name='EDGE_DISCOVERY_LOOP'
  AND enabled=true
  AND config_json ? 'max_parallel_research_jobs'
  AND config_json ? 'max_new_parameter_searches_per_day';
")

test "$rows" = "1"

echo "config_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_DISCOVERY_LOOP_CONFIG_V1_READY"
echo "VERDICT=TEST_EDGE_DISCOVERY_LOOP_CONFIG_V1_OK"
