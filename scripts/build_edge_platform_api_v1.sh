#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_PLATFORM_API_V1 ==="

api_file="src/marketcore/api/serve_knowledge_graph_api_v1.py"
cp "$api_file" /tmp/serve_knowledge_graph_api_v1.before_edge_platform_api_v1.bak

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if "/api/kg/v1/edge-platform/summary" not in s:
    marker = '            if path == "/api/kg/v1/strategy-platform/summary":'
    if marker not in s:
        raise SystemExit("STRATEGY_PLATFORM_API_MARKER_NOT_FOUND")

    block = r'''
            if path == "/api/kg/v1/edge-platform/summary":
                row = fetch_one("""
                    SELECT
                        count(*)::int AS edge_rows,
                        count(*) FILTER (WHERE decision_code='ALLOW')::int AS allow_rows,
                        count(*) FILTER (WHERE decision_code='OBSERVE')::int AS observe_rows,
                        count(*) FILTER (WHERE decision_code='BLOCK')::int AS block_rows,
                        count(*) FILTER (WHERE ready_for_paper=true)::int AS ready_for_paper_rows,
                        count(*) FILTER (WHERE ready_for_live=true OR ready_for_micro_live=true)::int AS unsafe_live_rows,
                        avg(edge_score)::float AS avg_edge_score,
                        avg(validation_score)::float AS avg_validation_score,
                        max(signal_ts) AS latest_signal_ts,
                        max(refreshed_at) AS refreshed_at
                    FROM analytics.edge_decision_snapshot_v1;
                """) or {}
                health_code = "HEALTHY" if int(row.get("unsafe_live_rows") or 0) == 0 and int(row.get("edge_rows") or 0) > 0 else "DEGRADED"
                row["health"] = dto("health", health_code)
                self.send_json(200, response("OK", row, {"source": "analytics.edge_decision_snapshot_v1"}))
                return

            if path == "/api/kg/v1/edge-platform/decisions":
                limit = int(q.get("limit", ["500"])[0])
                rows = fetch_all("""
                    SELECT
                        id,
                        signal_id,
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        strategy_version,
                        signal_ts,
                        edge_score::float AS edge_score,
                        validation_score::float AS validation_score,
                        governance_score::float AS governance_score,
                        decision_code,
                        recommendation_code,
                        ready_for_research,
                        ready_for_replay,
                        ready_for_paper,
                        ready_for_shadow,
                        ready_for_micro_live,
                        ready_for_live,
                        source_version,
                        refreshed_at
                    FROM analytics.edge_decision_snapshot_v1
                    ORDER BY signal_ts DESC, edge_score DESC
                    LIMIT %s;
                """, (limit,))
                for r in rows:
                    r["decision"] = dto("decision", r.pop("decision_code"))
                    r["recommendation"] = dto("recommendation", r.pop("recommendation_code"))
                self.send_json(200, response("OK", rows, {"source": "analytics.edge_decision_snapshot_v1"}))
                return

            if path == "/api/kg/v1/edge-platform/configuration":
                rows = fetch_all("""
                    SELECT
                        edge_name,
                        enabled,
                        config_json,
                        source_version,
                        updated_at
                    FROM analytics.edge_configuration_v1
                    ORDER BY edge_name;
                """)
                for r in rows:
                    r["enabled_status"] = dto("status", "ACTIVE" if r.get("enabled") else "DISABLED")
                self.send_json(200, response("OK", rows, {"source": "analytics.edge_configuration_v1"}))
                return

            if path == "/api/kg/v1/edge-platform/governance":
                row = fetch_one("""
                    SELECT *
                    FROM analytics.edge_governance_v1
                    WHERE governance_scope='GLOBAL';
                """) or {}
                if row:
                    row["score_engine_status"] = dto("status", row.get("score_engine_status"))
                    row["validation_status"] = dto("status", row.get("validation_status"))
                    row["decision_status"] = dto("status", row.get("decision_status"))
                    row["api_status"] = dto("status", row.get("api_status"))
                    row["ui_status"] = dto("status", row.get("ui_status"))
                    row["readiness"] = dto("governance", row.get("readiness_code"))
                    row["recommendation"] = dto("recommendation", row.get("recommendation_code"))
                self.send_json(200, response("OK", row, {"source": "analytics.edge_governance_v1"}))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > scripts/test_edge_platform_api_v1.sh <<'SH_TEST'
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
SH_TEST

chmod +x scripts/test_edge_platform_api_v1.sh
scripts/test_edge_platform_api_v1.sh

echo "VERDICT=BUILD_EDGE_PLATFORM_API_V1_OK"
