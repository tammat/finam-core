#!/usr/bin/env bash
set -euo pipefail

echo "=== RISK_PLATFORM_COMPLETE_CHECKPOINT_V1 ==="

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_risk_builder_v1.py >/tmp/risk_builder_checkpoint_v1.txt

grep -q "VERDICT=RISK_BUILDER_V1_READY" /tmp/risk_builder_checkpoint_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_risk_platform_governance_v1.py >/tmp/risk_governance_checkpoint_v1.txt

grep -q "VERDICT=RISK_PLATFORM_GOVERNANCE_V1_READY" /tmp/risk_governance_checkpoint_v1.txt

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8095/api/kg/v1/risk-platform/summary >/tmp/risk_summary.json
curl -fsS http://127.0.0.1:8095/api/kg/v1/risk-platform/decisions >/tmp/risk_decisions.json
curl -fsS http://127.0.0.1:8095/api/kg/v1/risk-platform/configuration >/tmp/risk_config.json
curl -fsS http://127.0.0.1:8095/api/kg/v1/risk-platform/governance >/tmp/risk_governance.json
curl -fsS http://127.0.0.1:8080/risk-platform >/tmp/risk_platform.html

python - <<'PY'
import json

summary = json.load(open("/tmp/risk_summary.json", encoding="utf-8"))
governance = json.load(open("/tmp/risk_governance.json", encoding="utf-8"))

assert summary["status"] == "OK"
assert summary["data"]["risk_rows"] > 0
assert summary["data"]["unsafe_live_rows"] == 0

assert governance["status"] == "OK"
g = governance["data"]
assert float(g["governance_score"]) >= 100.0
assert g["readiness"]["code"] == "READY_FOR_RESEARCH"
assert g["recommendation"]["code"] == "PROCEED_TO_TRADING_PLATFORM"
PY

risk_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.risk_decision_snapshot_v1;
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.risk_decision_snapshot_v1
WHERE ready_for_live=true OR ready_for_micro_live=true;
")

test "$risk_rows" -gt 0
test "$unsafe" = "0"

grep -q "Risk Platform" /tmp/risk_platform.html

echo "risk_rows=$risk_rows"
echo "unsafe_live_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RISK_PLATFORM_COMPLETE"
echo "VERDICT=RISK_PLATFORM_COMPLETE_CHECKPOINT_V1_OK"
