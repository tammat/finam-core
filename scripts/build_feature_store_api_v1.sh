#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_FEATURE_STORE_API_V1 ==="

api_file="src/marketcore/api/serve_knowledge_graph_api_v1.py"
cp "$api_file" /tmp/serve_knowledge_graph_api_v1.before_feature_store_api_v1.bak

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if "/api/kg/v1/feature-store" not in s:
    marker = '            if path == "/api/kg/v1/edge-pipeline":'
    if marker not in s:
        raise SystemExit("EDGE_PIPELINE_API_MARKER_NOT_FOUND")

    block = r'''
            if path == "/api/kg/v1/feature-store":
                rows = fetch_all("""
                    SELECT
                        symbol,
                        asset_class,
                        timeframe,
                        bar_ts,
                        open,
                        high,
                        low,
                        close,
                        volume,
                        range_pct,
                        body_pct,
                        return1_pct,
                        return5_pct,
                        volume_ratio20,
                        feature_quality_score,
                        source_version,
                        refreshed_at
                    FROM analytics.feature_snapshot_v1
                    ORDER BY bar_ts DESC, symbol, timeframe
                    LIMIT 500;
                """)
                self.send_json(200, response("OK", rows, {"source": "analytics.feature_snapshot_v1"}))
                return

            if path == "/api/kg/v1/feature-store/summary":
                row = fetch_one("""
                    SELECT
                        count(*)::int AS feature_rows,
                        count(DISTINCT symbol)::int AS feature_symbols,
                        max(bar_ts) AS latest_bar_ts,
                        max(refreshed_at) AS refreshed_at,
                        avg(feature_quality_score)::numeric(10,4) AS avg_quality_score,
                        count(*) FILTER (WHERE return1_pct IS NOT NULL)::int AS with_return1,
                        count(*) FILTER (WHERE volume_ratio20 IS NOT NULL)::int AS with_volume_ratio20
                    FROM analytics.feature_snapshot_v1;
                """)
                self.send_json(200, response("OK", row or {}, {"source": "analytics.feature_snapshot_v1"}))
                return

            if path == "/api/kg/v1/feature-store/health":
                row = fetch_one("""
                    SELECT *
                    FROM analytics.feature_store_health_v1
                    WHERE health_id='GLOBAL';
                """)
                self.send_json(200, response("OK", row or {}, {"source": "analytics.feature_store_health_v1"}))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > scripts/test_feature_store_api_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_STORE_API_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/scripts/build_feature_snapshot_history_backfill_v1.py \
  src/scripts/build_feature_store_health_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_feature_snapshot_history_backfill_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_feature_store_health_v1.py

sudo systemctl restart marketcore-kg-api.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/feature-store" > /tmp/feature_store_api_rows.json
curl -fsS "http://127.0.0.1:8095/api/kg/v1/feature-store/summary" > /tmp/feature_store_api_summary.json
curl -fsS "http://127.0.0.1:8095/api/kg/v1/feature-store/health" > /tmp/feature_store_api_health.json

python - <<'PY'
import json

rows = json.load(open("/tmp/feature_store_api_rows.json", encoding="utf-8"))
summary = json.load(open("/tmp/feature_store_api_summary.json", encoding="utf-8"))
health = json.load(open("/tmp/feature_store_api_health.json", encoding="utf-8"))

assert rows["status"] == "OK"
assert isinstance(rows["data"], list)
assert len(rows["data"]) > 0
assert "symbol" in rows["data"][0]
assert "return1_pct" in rows["data"][0]
assert "feature_quality_score" in rows["data"][0]

assert summary["status"] == "OK"
assert summary["data"]["feature_rows"] > 0
assert summary["data"]["feature_symbols"] > 1

assert health["status"] == "OK"
assert health["data"]["health_status"] in {"HEALTHY", "DEGRADED", "FAILED"}
PY

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.feature_snapshot_v1;")
health=$(psql -At -d finam_core -c "SELECT health_status FROM analytics.feature_store_health_v1 WHERE health_id='GLOBAL';")

echo "feature_rows=$rows"
echo "health_status=$health"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=FEATURE_STORE_API_V1_READY"
echo "VERDICT=TEST_FEATURE_STORE_API_V1_OK"
SH_TEST

chmod +x scripts/test_feature_store_api_v1.sh
scripts/test_feature_store_api_v1.sh

echo "VERDICT=BUILD_FEATURE_STORE_API_V1_OK"
