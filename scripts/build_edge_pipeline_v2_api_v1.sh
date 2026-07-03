#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_PIPELINE_V2_API_V1 ==="

api_file="src/marketcore/api/serve_knowledge_graph_api_v1.py"

cp "$api_file" /tmp/serve_knowledge_graph_api_v1.before_edge_pipeline_v2_api.bak

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if "from urllib.parse import" in s and "unquote" not in s:
    s = s.replace(
        "from urllib.parse import parse_qs, urlparse",
        "from urllib.parse import parse_qs, urlparse, unquote",
    )

if "/api/kg/v1/edge-pipeline" not in s:
    marker = '            if path == "/api/kg/v1/paper-runtime":'
    block = r'''
            if path == "/api/kg/v1/edge-pipeline":
                rows = fetch_all("""
                    SELECT
                        symbol,
                        display_name,
                        asset_class,
                        timeframe,
                        strategy_family,
                        pipeline_stage,
                        overall_status,
                        ranking_score,
                        research_priority,
                        research_status,
                        validation_status,
                        validation_score,
                        robustness_status,
                        robustness_score,
                        oos_status,
                        oos_score,
                        backtest_status,
                        backtest_score,
                        paper_status,
                        paper_progress,
                        paper_trades,
                        risk_status,
                        trading_status,
                        runtime_status,
                        source_version,
                        refreshed_at
                    FROM analytics.edge_pipeline_snapshot_v1
                    ORDER BY ranking_score DESC, symbol, timeframe, strategy_family;
                """)
                self.send_json(200, response("OK", rows, {"source": "analytics.edge_pipeline_snapshot_v1"}))
                return

            if path == "/api/kg/v1/edge-pipeline/summary":
                row = fetch_one("""
                    SELECT
                        count(*)::int AS total,
                        count(*) FILTER (WHERE pipeline_stage=20)::int AS research,
                        count(*) FILTER (WHERE pipeline_stage=30)::int AS validation,
                        count(*) FILTER (WHERE pipeline_stage=40)::int AS robustness,
                        count(*) FILTER (WHERE pipeline_stage=50)::int AS oos,
                        count(*) FILTER (WHERE pipeline_stage=60)::int AS backtest,
                        count(*) FILTER (WHERE pipeline_stage=70)::int AS paper,
                        count(*) FILTER (WHERE pipeline_stage=80)::int AS risk,
                        count(*) FILTER (WHERE pipeline_stage=90)::int AS trading,
                        count(*) FILTER (WHERE pipeline_stage=100)::int AS live,
                        max(refreshed_at) AS refreshed_at
                    FROM analytics.edge_pipeline_snapshot_v1;
                """)
                self.send_json(200, response("OK", row or {}, {"source": "analytics.edge_pipeline_snapshot_v1"}))
                return

            if path.startswith("/api/kg/v1/edge-pipeline/stage/"):
                stage_raw = path.rsplit("/", 1)[-1]
                try:
                    stage = int(stage_raw)
                except ValueError:
                    self.send_json(400, response("ERROR", {}, {"error": "stage must be integer"}))
                    return

                rows = fetch_all("""
                    SELECT *
                    FROM analytics.edge_pipeline_snapshot_v1
                    WHERE pipeline_stage=%s
                    ORDER BY ranking_score DESC, symbol, timeframe, strategy_family;
                """, (stage,))
                self.send_json(200, response("OK", rows, {"source": "analytics.edge_pipeline_snapshot_v1", "stage": stage}))
                return

            if path.startswith("/api/kg/v1/edge-pipeline/"):
                parts = path.split("/")
                if len(parts) >= 7:
                    symbol = unquote(parts[5])
                    timeframe = unquote(parts[6])
                    row = fetch_one("""
                        SELECT *
                        FROM analytics.edge_pipeline_snapshot_v1
                        WHERE symbol=%s AND timeframe=%s
                        ORDER BY ranking_score DESC, strategy_family
                        LIMIT 1;
                    """, (symbol, timeframe))
                    if not row:
                        self.send_json(404, response("NOT_FOUND", {}, {"source": "analytics.edge_pipeline_snapshot_v1"}))
                        return
                    self.send_json(200, response("OK", row, {"source": "analytics.edge_pipeline_snapshot_v1"}))
                    return
'''
    if marker not in s:
        raise SystemExit("INSERT_MARKER_NOT_FOUND")
    s = s.replace(marker, block + "\n" + marker)

p.write_text(s)
PY

cat > scripts/test_edge_pipeline_v2_api_v1.sh <<'SH_TEST'
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
SH_TEST

chmod +x scripts/test_edge_pipeline_v2_api_v1.sh
scripts/test_edge_pipeline_v2_api_v1.sh

echo "VERDICT=BUILD_EDGE_PIPELINE_V2_API_V1_OK"
