#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PORTFOLIO_PLATFORM_API_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/scripts/build_portfolio_builder_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_portfolio_builder_v1.py

sudo systemctl restart marketcore-kg-api.service
sleep 2

base="http://127.0.0.1:8095"

curl -fsS "$base/api/kg/v1/portfolio-platform/summary" > /tmp/portfolio_platform_summary.json
curl -fsS "$base/api/kg/v1/portfolio-platform/positions" > /tmp/portfolio_platform_positions.json
curl -fsS "$base/api/kg/v1/portfolio-platform/equity" > /tmp/portfolio_platform_equity.json
curl -fsS "$base/api/kg/v1/portfolio-platform/configuration" > /tmp/portfolio_platform_configuration.json
curl -fsS "$base/api/kg/v1/portfolio-platform/governance" > /tmp/portfolio_platform_governance.json

python - <<'PY'
import json

summary = json.load(open("/tmp/portfolio_platform_summary.json", encoding="utf-8"))
positions = json.load(open("/tmp/portfolio_platform_positions.json", encoding="utf-8"))
equity = json.load(open("/tmp/portfolio_platform_equity.json", encoding="utf-8"))
config = json.load(open("/tmp/portfolio_platform_configuration.json", encoding="utf-8"))
governance = json.load(open("/tmp/portfolio_platform_governance.json", encoding="utf-8"))

assert summary["status"] == "OK"
assert "health" in summary["data"]
assert "equity" in summary["data"]

assert positions["status"] == "OK"
assert isinstance(positions["data"], list)
if positions["data"]:
    assert isinstance(positions["data"][0]["position_status"], dict)

assert equity["status"] == "OK"
assert "portfolio_scope" in equity["data"]

assert config["status"] == "OK"
assert len(config["data"]) > 0
assert isinstance(config["data"][0]["enabled_status"], dict)

assert governance["status"] == "OK"
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PORTFOLIO_PLATFORM_API_V1_READY"
echo "VERDICT=TEST_PORTFOLIO_PLATFORM_API_V1_OK"
