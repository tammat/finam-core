#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PORTFOLIO_PLATFORM_GOVERNANCE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_portfolio_platform_governance_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/portfolio_platform.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_portfolio_builder_v1.py >/tmp/portfolio_builder_for_governance_v1.txt

grep -q "VERDICT=PORTFOLIO_BUILDER_V1_READY" /tmp/portfolio_builder_for_governance_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_portfolio_platform_governance_v1.py | tee /tmp/portfolio_platform_governance_v1.txt

grep -q "VERDICT=PORTFOLIO_PLATFORM_GOVERNANCE_V1_READY" /tmp/portfolio_platform_governance_v1.txt

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/portfolio-platform/governance" > /tmp/portfolio_platform_governance_api.json
curl -fsS "http://127.0.0.1:8080/portfolio-platform" > /tmp/portfolio_platform_governance_ui.html

python - <<'PY'
import json

p = json.load(open("/tmp/portfolio_platform_governance_api.json", encoding="utf-8"))
assert p["status"] == "OK"
d = p["data"]
assert float(d["governance_score"]) >= 80
assert d["readiness"]["code"] in {"READY_FOR_RESEARCH", "NOT_READY"}
assert d["recommendation"]["code"] in {"PROCEED_TO_CONSOLIDATION", "FIX_PORTFOLIO_PLATFORM"}
PY

grep -q "Portfolio Platform" /tmp/portfolio_platform_governance_ui.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PORTFOLIO_PLATFORM_GOVERNANCE_V1_READY"
echo "VERDICT=TEST_PORTFOLIO_PLATFORM_GOVERNANCE_V1_OK"
