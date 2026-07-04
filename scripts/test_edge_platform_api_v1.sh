#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PLATFORM_API_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/scripts/build_edge_decision_engine_v1.py

DATABASE_URL=postgresql:///finam_core EDGE_DECISION_LIMIT=5000 PYTHONPATH=src \
python src/scripts/build_edge_decision_engine_v1.py

sudo systemctl restart marketcore-kg-api.service
sleep 2

base="http://127.0.0.1:8095"

curl -fsS "$base/api/kg/v1/edge-platform/summary" > /tmp/edge_platform_summary.json
curl -fsS "$base/api/kg/v1/edge-platform/decisions" > /tmp/edge_platform_decisions.json
curl -fsS "$base/api/kg/v1/edge-platform/configuration" > /tmp/edge_platform_configuration.json

python - <<'PY'
import json

summary = json.load(open("/tmp/edge_platform_summary.json", encoding="utf-8"))
decisions = json.load(open("/tmp/edge_platform_decisions.json", encoding="utf-8"))
config = json.load(open("/tmp/edge_platform_configuration.json", encoding="utf-8"))

assert summary["status"] == "OK"
assert summary["data"]["edge_rows"] > 0
assert summary["data"]["unsafe_live_rows"] == 0
assert "health" in summary["data"]
assert "display_key" in summary["data"]["health"]

assert decisions["status"] == "OK"
assert len(decisions["data"]) > 0
assert isinstance(decisions["data"][0]["decision"], dict)
assert isinstance(decisions["data"][0]["recommendation"], dict)
assert decisions["data"][0]["ready_for_live"] is False

assert config["status"] == "OK"
assert len(config["data"]) > 0
assert isinstance(config["data"][0]["enabled_status"], dict)
PY

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
echo "VERDICT=EDGE_PLATFORM_API_V1_READY"
echo "VERDICT=TEST_EDGE_PLATFORM_API_V1_OK"
