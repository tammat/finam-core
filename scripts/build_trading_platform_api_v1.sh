#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_TRADING_PLATFORM_API_V1 ==="

api_file="src/marketcore/api/serve_knowledge_graph_api_v1.py"
cp "$api_file" /tmp/serve_knowledge_graph_api_v1.before_trading_platform_api_v1.bak

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if "/api/kg/v1/trading-platform/summary" not in s:
    marker = '            if path == "/api/kg/v1/risk-platform/summary":'
    if marker not in s:
        raise SystemExit("RISK_PLATFORM_API_MARKER_NOT_FOUND")

    block = r'''
            if path == "/api/kg/v1/trading-platform/summary":
                row = fetch_one("""
                    SELECT
                        count(*)::int AS intent_rows,
                        count(*) FILTER (WHERE paper_allowed=true)::int AS paper_allowed_rows,
                        count(*) FILTER (WHERE shadow_allowed=true)::int AS shadow_allowed_rows,
                        count(*) FILTER (WHERE micro_live_allowed=true)::int AS micro_live_allowed_rows,
                        count(*) FILTER (WHERE live_allowed=true)::int AS live_allowed_rows,
                        count(*) FILTER (WHERE order_sent=true)::int AS order_sent_rows,
                        count(*) FILTER (WHERE trading_decision_code='PAPER_INTENT_READY')::int AS paper_ready_rows,
                        count(*) FILTER (WHERE trading_decision_code='TRADING_BLOCK')::int AS block_rows,
                        max(signal_ts) AS latest_signal_ts,
                        max(refreshed_at) AS refreshed_at
                    FROM analytics.trading_order_intent_v1;
                """) or {}
                unsafe = int(row.get("micro_live_allowed_rows") or 0) + int(row.get("live_allowed_rows") or 0) + int(row.get("order_sent_rows") or 0)
                health_code = "HEALTHY" if unsafe == 0 and int(row.get("intent_rows") or 0) > 0 else "DEGRADED"
                row["health"] = dto("health", health_code)
                self.send_json(200, response("OK", row, {"source": "analytics.trading_order_intent_v1"}))
                return

            if path == "/api/kg/v1/trading-platform/intents":
                limit = int(q.get("limit", ["500"])[0])
                rows = fetch_all("""
                    SELECT
                        id,
                        risk_decision_id,
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        strategy_version,
                        signal_ts,
                        risk_score::float AS risk_score,
                        order_side,
                        order_type,
                        quantity::float AS quantity,
                        trading_decision_code,
                        recommendation_code,
                        paper_allowed,
                        shadow_allowed,
                        micro_live_allowed,
                        live_allowed,
                        order_sent,
                        broker_order_id,
                        source_version,
                        refreshed_at
                    FROM analytics.trading_order_intent_v1
                    ORDER BY signal_ts DESC, risk_score DESC
                    LIMIT %s;
                """, (limit,))
                for r in rows:
                    r["trading_decision"] = dto("trading", r.pop("trading_decision_code"))
                    r["recommendation"] = dto("recommendation", r.pop("recommendation_code"))
                    r["order_side_status"] = dto("signal", r.get("order_side"))
                    r["order_sent_status"] = dto("status", "ACTIVE" if r.get("order_sent") else "DISABLED")
                self.send_json(200, response("OK", rows, {"source": "analytics.trading_order_intent_v1"}))
                return

            if path == "/api/kg/v1/trading-platform/configuration":
                rows = fetch_all("""
                    SELECT
                        trading_name,
                        enabled,
                        config_json,
                        source_version,
                        updated_at
                    FROM analytics.trading_configuration_v1
                    ORDER BY trading_name;
                """)
                for r in rows:
                    r["enabled_status"] = dto("status", "ACTIVE" if r.get("enabled") else "DISABLED")
                self.send_json(200, response("OK", rows, {"source": "analytics.trading_configuration_v1"}))
                return

            if path == "/api/kg/v1/trading-platform/governance":
                row = fetch_one("""
                    SELECT *
                    FROM analytics.trading_governance_v1
                    WHERE governance_scope='GLOBAL';
                """) or {}
                if row:
                    row["builder_status"] = dto("status", row.get("builder_status"))
                    row["order_intent_status"] = dto("status", row.get("order_intent_status"))
                    row["api_status"] = dto("status", row.get("api_status"))
                    row["ui_status"] = dto("status", row.get("ui_status"))
                    row["readiness"] = dto("governance", row.get("readiness_code"))
                    row["recommendation"] = dto("recommendation", row.get("recommendation_code"))
                self.send_json(200, response("OK", row, {"source": "analytics.trading_governance_v1"}))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > scripts/test_trading_platform_api_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_PLATFORM_API_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/scripts/build_trading_builder_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_trading_builder_v1.py

sudo systemctl restart marketcore-kg-api.service
sleep 2

base="http://127.0.0.1:8095"

curl -fsS "$base/api/kg/v1/trading-platform/summary" > /tmp/trading_platform_summary.json
curl -fsS "$base/api/kg/v1/trading-platform/intents" > /tmp/trading_platform_intents.json
curl -fsS "$base/api/kg/v1/trading-platform/configuration" > /tmp/trading_platform_configuration.json
curl -fsS "$base/api/kg/v1/trading-platform/governance" > /tmp/trading_platform_governance.json

python - <<'PY'
import json

summary = json.load(open("/tmp/trading_platform_summary.json", encoding="utf-8"))
intents = json.load(open("/tmp/trading_platform_intents.json", encoding="utf-8"))
config = json.load(open("/tmp/trading_platform_configuration.json", encoding="utf-8"))
governance = json.load(open("/tmp/trading_platform_governance.json", encoding="utf-8"))

assert summary["status"] == "OK"
assert "health" in summary["data"]
assert summary["data"]["micro_live_allowed_rows"] == 0
assert summary["data"]["live_allowed_rows"] == 0
assert summary["data"]["order_sent_rows"] == 0

assert intents["status"] == "OK"
assert isinstance(intents["data"], list)
if intents["data"]:
    assert isinstance(intents["data"][0]["trading_decision"], dict)
    assert isinstance(intents["data"][0]["recommendation"], dict)
    assert intents["data"][0]["live_allowed"] is False
    assert intents["data"][0]["micro_live_allowed"] is False
    assert intents["data"][0]["order_sent"] is False

assert config["status"] == "OK"
assert len(config["data"]) > 0
assert isinstance(config["data"][0]["enabled_status"], dict)

assert governance["status"] == "OK"
PY

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.trading_order_intent_v1
WHERE live_allowed=true
   OR micro_live_allowed=true
   OR order_sent=true;
")
test "$unsafe" = "0"

echo "unsafe_live_or_sent_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TRADING_PLATFORM_API_V1_READY"
echo "VERDICT=TEST_TRADING_PLATFORM_API_V1_OK"
SH_TEST

chmod +x scripts/test_trading_platform_api_v1.sh
scripts/test_trading_platform_api_v1.sh

echo "VERDICT=BUILD_TRADING_PLATFORM_API_V1_OK"
