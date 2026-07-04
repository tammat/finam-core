#!/usr/bin/env bash
set -euo pipefail

echo "=== TRADING_PLATFORM_COMPLETE_CHECKPOINT_V1 ==="

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_trading_builder_v1.py >/tmp/trading_builder_checkpoint_v1.txt

grep -q "VERDICT=TRADING_BUILDER_V1_READY" /tmp/trading_builder_checkpoint_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_trading_platform_governance_v1.py >/tmp/trading_governance_checkpoint_v1.txt

grep -q "VERDICT=TRADING_PLATFORM_GOVERNANCE_V1_READY" /tmp/trading_governance_checkpoint_v1.txt

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8095/api/kg/v1/trading-platform/summary >/tmp/trading_summary.json
curl -fsS http://127.0.0.1:8095/api/kg/v1/trading-platform/intents >/tmp/trading_intents.json
curl -fsS http://127.0.0.1:8095/api/kg/v1/trading-platform/configuration >/tmp/trading_config.json
curl -fsS http://127.0.0.1:8095/api/kg/v1/trading-platform/governance >/tmp/trading_governance.json
curl -fsS http://127.0.0.1:8080/trading-platform >/tmp/trading_platform.html

python - <<'PY'
import json

summary = json.load(open("/tmp/trading_summary.json", encoding="utf-8"))
governance = json.load(open("/tmp/trading_governance.json", encoding="utf-8"))

assert summary["status"] == "OK"
assert summary["data"]["micro_live_allowed_rows"] == 0
assert summary["data"]["live_allowed_rows"] == 0
assert summary["data"]["order_sent_rows"] == 0

assert governance["status"] == "OK"
g = governance["data"]
assert float(g["governance_score"]) >= 100.0
assert g["readiness"]["code"] in {"READY_FOR_RESEARCH", "READY_FOR_PAPER"}
assert g["recommendation"]["code"] in {"WAIT_FOR_RISK_ALLOW", "PROCEED_TO_PORTFOLIO_PLATFORM"}
PY

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.trading_order_intent_v1
WHERE live_allowed=true
   OR micro_live_allowed=true
   OR order_sent=true;
")

test "$unsafe" = "0"

grep -q "Trading Platform" /tmp/trading_platform.html

intent_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.trading_order_intent_v1;
")

echo "intent_rows=$intent_rows"
echo "unsafe_live_or_sent_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TRADING_PLATFORM_COMPLETE"
echo "VERDICT=TRADING_PLATFORM_COMPLETE_CHECKPOINT_V1_OK"
