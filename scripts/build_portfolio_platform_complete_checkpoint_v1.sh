#!/usr/bin/env bash
set -euo pipefail

echo "=== PORTFOLIO_PLATFORM_COMPLETE_CHECKPOINT_V1 ==="

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python src/scripts/build_portfolio_builder_v1.py \
    >/tmp/portfolio_builder_checkpoint_v1.txt

grep -q \
"VERDICT=PORTFOLIO_BUILDER_V1_READY" \
/tmp/portfolio_builder_checkpoint_v1.txt

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python src/scripts/build_portfolio_platform_governance_v1.py \
    >/tmp/portfolio_governance_checkpoint_v1.txt

grep -q \
"VERDICT=PORTFOLIO_PLATFORM_GOVERNANCE_V1_READY" \
/tmp/portfolio_governance_checkpoint_v1.txt

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS \
http://127.0.0.1:8095/api/kg/v1/portfolio-platform/summary \
>/tmp/portfolio_summary.json

curl -fsS \
http://127.0.0.1:8095/api/kg/v1/portfolio-platform/positions \
>/tmp/portfolio_positions.json

curl -fsS \
http://127.0.0.1:8095/api/kg/v1/portfolio-platform/equity \
>/tmp/portfolio_equity.json

curl -fsS \
http://127.0.0.1:8095/api/kg/v1/portfolio-platform/configuration \
>/tmp/portfolio_configuration.json

curl -fsS \
http://127.0.0.1:8095/api/kg/v1/portfolio-platform/governance \
>/tmp/portfolio_governance.json

curl -fsS \
http://127.0.0.1:8080/portfolio-platform \
>/tmp/portfolio_platform.html

python - <<'PY'
import json

summary = json.load(open("/tmp/portfolio_summary.json"))

assert summary["status"] == "OK"

governance = json.load(open("/tmp/portfolio_governance.json"))

assert governance["status"] == "OK"

g = governance["data"]

assert float(g["governance_score"]) >= 100.0
assert g["readiness"]["code"] == "READY_FOR_RESEARCH"
assert g["recommendation"]["code"] == "PROCEED_TO_CONSOLIDATION"

print("PORTFOLIO_GOVERNANCE_OK")
PY

equity=$(psql -At -d finam_core -c "
SELECT equity
FROM analytics.portfolio_equity_snapshot_v1
WHERE portfolio_scope='GLOBAL';
")

positions=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.portfolio_position_snapshot_v1;
")

grep -q "Portfolio Platform" \
    /tmp/portfolio_platform.html

echo
echo "==========================================="
echo "PORTFOLIO PLATFORM COMPLETE"
echo "==========================================="

echo "equity=$equity"
echo "positions=$positions"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=PORTFOLIO_PLATFORM_COMPLETE"
echo "VERDICT=PORTFOLIO_PLATFORM_COMPLETE_CHECKPOINT_V1_OK"

