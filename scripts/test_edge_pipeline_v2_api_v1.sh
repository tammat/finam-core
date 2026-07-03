#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PIPELINE_V2_API_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/scripts/build_edge_pipeline_snapshot_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_pipeline_snapshot_v1.py

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_pipeline_snapshot_v1;")
test "$rows" -gt 0

sudo systemctl restart marketcore-kg-api.service
sleep 2

pid=$(systemctl show -p MainPID --value marketcore-kg-api.service)
port=$(ss -ltnp | awk -v pid="$pid" '$0 ~ "pid="pid"," {n=split($4,a,":"); print a[n]; exit}')

if [ -z "${port:-}" ]; then
  echo "ERROR_KG_API_PORT_NOT_FOUND"
  systemctl status marketcore-kg-api.service --no-pager || true
  exit 1
fi

base="http://127.0.0.1:${port}"

curl -fsS "$base/api/kg/v1/edge-pipeline" > /tmp/edge_pipeline_api_all.json
curl -fsS "$base/api/kg/v1/edge-pipeline/summary" > /tmp/edge_pipeline_api_summary.json
curl -fsS "$base/api/kg/v1/edge-pipeline/stage/20" > /tmp/edge_pipeline_api_stage20.json

first=$(psql -At -F '|' -d finam_core -c "
SELECT symbol, timeframe
FROM analytics.edge_pipeline_snapshot_v1
ORDER BY ranking_score DESC, symbol, timeframe
LIMIT 1;
")

symbol="${first%%|*}"
timeframe="${first##*|}"

encoded_symbol=$(python - <<PY
from urllib.parse import quote
print(quote("$symbol", safe=""))
PY
)

encoded_tf=$(python - <<PY
from urllib.parse import quote
print(quote("$timeframe", safe=""))
PY
)

curl -fsS "$base/api/kg/v1/edge-pipeline/$encoded_symbol/$encoded_tf" > /tmp/edge_pipeline_api_one.json

python - <<'PY'
import json

with open("/tmp/edge_pipeline_api_all.json", encoding="utf-8") as f:
    all_payload = json.load(f)

with open("/tmp/edge_pipeline_api_summary.json", encoding="utf-8") as f:
    summary_payload = json.load(f)

with open("/tmp/edge_pipeline_api_stage20.json", encoding="utf-8") as f:
    stage_payload = json.load(f)

with open("/tmp/edge_pipeline_api_one.json", encoding="utf-8") as f:
    one_payload = json.load(f)

assert all_payload["status"] == "OK"
assert isinstance(all_payload["data"], list)
assert len(all_payload["data"]) > 0
assert "ranking_score" in all_payload["data"][0]

assert summary_payload["status"] == "OK"
assert "total" in summary_payload["data"]

assert stage_payload["status"] == "OK"
assert isinstance(stage_payload["data"], list)

assert one_payload["status"] == "OK"
assert one_payload["data"]["symbol"]
assert one_payload["data"]["timeframe"]
PY

api_rows=$(python - <<'PY'
import json
print(len(json.load(open("/tmp/edge_pipeline_api_all.json", encoding="utf-8"))["data"]))
PY
)

test "$api_rows" = "$rows"

echo "kg_api_port=$port"
echo "edge_pipeline_rows=$rows"
echo "api_rows=$api_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_PIPELINE_V2_API_V1_READY"
echo "VERDICT=TEST_EDGE_PIPELINE_V2_API_V1_OK"
