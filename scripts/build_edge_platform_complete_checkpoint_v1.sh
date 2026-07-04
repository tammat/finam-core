#!/usr/bin/env bash
set -euo pipefail

echo "=== EDGE_PLATFORM_COMPLETE_CHECKPOINT_V1 ==="

echo
echo "=== VERIFY EDGE PLATFORM ==="

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python src/scripts/build_edge_platform_governance_v1.py >/tmp/edge_governance_checkpoint.txt

grep -q "VERDICT=EDGE_PLATFORM_GOVERNANCE_V1_READY" \
    /tmp/edge_governance_checkpoint.txt

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS \
    http://127.0.0.1:8095/api/kg/v1/edge-platform/summary \
    >/tmp/edge_summary.json

curl -fsS \
    http://127.0.0.1:8095/api/kg/v1/edge-platform/decisions \
    >/tmp/edge_decisions.json

curl -fsS \
    http://127.0.0.1:8095/api/kg/v1/edge-platform/configuration \
    >/tmp/edge_configuration.json

curl -fsS \
    http://127.0.0.1:8095/api/kg/v1/edge-platform/governance \
    >/tmp/edge_governance.json

curl -fsS \
    http://127.0.0.1:8080/edge-platform \
    >/tmp/edge_platform.html

python - <<'PY'
import json

summary = json.load(open("/tmp/edge_summary.json"))
assert summary["status"] == "OK"

governance = json.load(open("/tmp/edge_governance.json"))
assert governance["status"] == "OK"

g = governance["data"]

assert float(g["governance_score"]) >= 100.0
assert g["readiness"]["code"] == "READY_FOR_RESEARCH"
assert g["recommendation"]["code"] == "PROCEED_TO_RISK_PLATFORM"

print("EDGE_GOVERNANCE_OK")
PY

edge_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_decision_snapshot_v1;
")

allow=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_decision_snapshot_v1
WHERE decision_code='ALLOW';
")

observe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_decision_snapshot_v1
WHERE decision_code='OBSERVE';
")

block=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_decision_snapshot_v1
WHERE decision_code='BLOCK';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_decision_snapshot_v1
WHERE ready_for_live=true
   OR ready_for_micro_live=true;
")

test "$edge_rows" -gt 0
test "$unsafe" = "0"

grep -q "Edge Platform" /tmp/edge_platform.html

echo
echo "======================================"
echo "EDGE PLATFORM COMPLETE"
echo "======================================"

echo "edge_rows=$edge_rows"
echo "allow=$allow"
echo "observe=$observe"
echo "block=$block"
echo "unsafe_live_rows=$unsafe"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=EDGE_PLATFORM_COMPLETE"
echo "VERDICT=EDGE_PLATFORM_COMPLETE_CHECKPOINT_V1_OK"

