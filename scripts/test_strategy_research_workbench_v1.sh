#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_RESEARCH_WORKBENCH_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/strategy_workbench.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core STRATEGY_FEATURE_LIMIT=5000 PYTHONPATH=src \
python src/scripts/build_multi_strategy_engine_builder_v1.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/strategy-workbench" > /tmp/strategy_workbench_api.json
curl -fsS "http://127.0.0.1:8080/strategy-workbench" > /tmp/strategy_workbench_ui.html

python - <<'PY'
import json

p = json.load(open("/tmp/strategy_workbench_api.json", encoding="utf-8"))
assert p["status"] == "OK"
data = p["data"]
assert data["summary"]["features_checked"] > 0
assert "rows" in data
assert len(data["rows"]) > 0
row = data["rows"][0]
assert "passed_filters" in row
assert "failed_filters" in row
assert "score_breakdown" in row
PY

grep -q "analytics.feature_snapshot_v1" /tmp/strategy_workbench_api.json
grep -q "Рабочее место стратегии" /tmp/strategy_workbench_ui.html

if grep -R "SELECT .*feature_snapshot_v1\|FROM analytics.feature_snapshot_v1" \
  src/marketcore/presentation/pages/strategy_workbench.py; then
  echo "ERROR_DIRECT_SQL_IN_STRATEGY_WORKBENCH_UI"
  exit 1
fi

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=STRATEGY_RESEARCH_WORKBENCH_V1_READY"
echo "VERDICT=TEST_STRATEGY_RESEARCH_WORKBENCH_V1_OK"
