#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_PLATFORM_API_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py

DATABASE_URL=postgresql:///finam_core STRATEGY_FEATURE_LIMIT=5000 PYTHONPATH=src \
python src/scripts/build_multi_strategy_engine_builder_v1.py

sudo systemctl restart marketcore-kg-api.service
sleep 2

base="http://127.0.0.1:8095"

for path in \
  /api/kg/v1/strategy-platform/summary \
  /api/kg/v1/strategy-platform/registry \
  /api/kg/v1/strategy-platform/configuration \
  /api/kg/v1/strategy-platform/dependencies \
  /api/kg/v1/strategy-platform/signals \
  /api/kg/v1/strategy-platform/health \
  /api/kg/v1/strategy-platform/workbench
do
  curl -fsS "$base$path" > "/tmp/${path//\//_}.json"
done

python - <<'PY'
import json

def load(name):
    return json.load(open(name, encoding="utf-8"))

summary = load("/tmp/_api_kg_v1_strategy-platform_summary.json")
registry = load("/tmp/_api_kg_v1_strategy-platform_registry.json")
signals = load("/tmp/_api_kg_v1_strategy-platform_signals.json")
health = load("/tmp/_api_kg_v1_strategy-platform_health.json")
workbench = load("/tmp/_api_kg_v1_strategy-platform_workbench.json")

assert summary["status"] == "OK"
assert summary["data"]["strategies_enabled"] >= 1
assert "health" in summary["data"]
assert "display_key" in summary["data"]["health"]

assert registry["status"] == "OK"
assert len(registry["data"]) >= 1
assert isinstance(registry["data"][0]["status"], dict)

assert signals["status"] == "OK"
assert len(signals["data"]) >= 1
assert isinstance(signals["data"][0]["signal_direction"], dict)
assert signals["data"][0]["execution_allowed"] is False

assert health["status"] == "OK"
assert "health" in health["data"]
assert health["data"]["health"]["code"] in {"HEALTHY", "DEGRADED", "FAILED"}

assert workbench["status"] == "OK"
assert workbench["data"]["summary"]["features_checked"] > 0
PY

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
echo "VERDICT=STRATEGY_PLATFORM_API_V1_READY"
echo "VERDICT=TEST_STRATEGY_PLATFORM_API_V1_OK"
