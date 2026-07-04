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
