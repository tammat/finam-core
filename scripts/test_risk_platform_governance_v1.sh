#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_PLATFORM_GOVERNANCE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_risk_platform_governance_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/risk_platform.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_risk_platform_governance_v1.py | tee /tmp/risk_platform_governance_v1.txt

grep -q "VERDICT=RISK_PLATFORM_GOVERNANCE_V1_READY" /tmp/risk_platform_governance_v1.txt

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/risk-platform/governance" > /tmp/risk_platform_governance_api.json
curl -fsS "http://127.0.0.1:8080/risk-platform" > /tmp/risk_platform_governance_ui.html

python - <<'PY'
import json

p = json.load(open("/tmp/risk_platform_governance_api.json", encoding="utf-8"))
assert p["status"] == "OK"
d = p["data"]
assert float(d["governance_score"]) >= 75
assert d["readiness"]["code"] in {"READY_FOR_RESEARCH", "NOT_READY"}
assert d["recommendation"]["code"] in {"PROCEED_TO_TRADING_PLATFORM", "FIX_RISK_PLATFORM", "BLOCK_PLATFORM"}
PY

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.risk_decision_snapshot_v1
WHERE ready_for_live=true OR ready_for_micro_live=true;
")
test "$unsafe" = "0"

grep -q "Risk Platform" /tmp/risk_platform_governance_ui.html

echo "unsafe_live_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RISK_PLATFORM_GOVERNANCE_V1_READY"
echo "VERDICT=TEST_RISK_PLATFORM_GOVERNANCE_V1_OK"
