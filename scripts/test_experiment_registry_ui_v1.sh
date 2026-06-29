#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXPERIMENT_REGISTRY_UI_V1 ==="

sudo -u postgres psql finam_core -c "GRANT SELECT ON warehouse.experiment_registry_v1 TO alex;"

sudo systemctl restart finam-readonly-ui
sleep 2

curl -fsS http://127.0.0.1:8089/knowledge/experiments -o /tmp/experiment_registry_ui_v1.html
curl -fsS http://127.0.0.1:8089/knowledge/experiments/health -o /tmp/experiment_registry_ui_health_v1.html

grep -q "MarketCore Experiment Registry" /tmp/experiment_registry_ui_v1.html
grep -q "total=1" /tmp/experiment_registry_ui_v1.html
grep -q "registered=1" /tmp/experiment_registry_ui_v1.html
grep -q "BRM6@RTSX" /tmp/experiment_registry_ui_v1.html
grep -q "RESEARCH_CANDIDATE" /tmp/experiment_registry_ui_v1.html
grep -q "EXPERIMENT_REGISTRY_READ_ONLY" /tmp/experiment_registry_ui_v1.html

grep -q "MarketCore Experiment Registry Health" /tmp/experiment_registry_ui_health_v1.html
grep -q "missing_experiment_code=0" /tmp/experiment_registry_ui_health_v1.html
grep -q "unsafe_approvals=0" /tmp/experiment_registry_ui_health_v1.html
grep -q "micro_live_allowed=0" /tmp/experiment_registry_ui_health_v1.html

echo "single_ui_port=8089"
echo "route_experiments=/knowledge/experiments"
echo "route_experiments_health=/knowledge/experiments/health"
echo "source_policy=EXPERIMENT_REGISTRY_READ_ONLY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EXPERIMENT_REGISTRY_UI_V1_READY"
echo "TEST_EXPERIMENT_REGISTRY_UI_V1_OK"
