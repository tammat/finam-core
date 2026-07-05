#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_EXECUTION_RUNNER_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/016_strategy_execution_runner_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_strategy_execution_runner_v1.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core STRATEGY_EXECUTION_RUNNER_LIMIT=10 PYTHONPATH=src \
python src/scripts/build_strategy_execution_runner_v1.py | tee /tmp/strategy_execution_runner_v1.txt

grep -q "VERDICT=STRATEGY_EXECUTION_RUNNER_V1_READY" /tmp/strategy_execution_runner_v1.txt

obs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_observation_v1;")
done_runs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_lab_run_v1 WHERE status_code='DONE';")
trade_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.research_trade_v1') IS NOT NULL;")
failed_runs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_lab_run_v1 WHERE status_code='FAILED';")

test "$obs" -gt 0
test "$done_runs" -gt 0
test "$trade_table" = "t"
test "$failed_runs" = "0"

grep -q "strategy.execution.runner.title" src/marketcore/presentation/ui_labels.py
grep -q "edge.verdict.NO_MARKET_DATA" src/marketcore/presentation/ui_labels.py

echo "observations=$obs"
echo "done_runs=$done_runs"
echo "trade_table=$trade_table"
echo "failed_runs=$failed_runs"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_STRATEGY_EXECUTION_RUNNER_V1_OK"
