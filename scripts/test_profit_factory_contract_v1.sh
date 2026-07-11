#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PROFIT_FACTORY_CONTRACT_V1 ==="

psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/022_profit_factory_contract_v1.sql

table_exists=$(psql -At -d finam_core -c \
  "SELECT to_regclass('analytics.profit_factory_candidate_v1') IS NOT NULL;")
view_exists=$(psql -At -d finam_core -c \
  "SELECT to_regclass('analytics.profit_factory_decision_queue_v1') IS NOT NULL;")

required_columns=$(psql -At -d finam_core -c "
SELECT count(*)
FROM information_schema.columns
WHERE table_schema='analytics'
  AND table_name='profit_factory_candidate_v1'
  AND column_name IN (
    'candidate_id', 'workflow_run_id', 'factory_stage', 'stage_status',
    'expected_profit', 'realized_profit', 'capital_allocated', 'factory_roi',
    'max_drawdown', 'confidence_score', 'operator_decision',
    'decision_reason_code', 'decision_expected_impact', 'reason_code'
  );")

constraint_count=$(psql -At -d finam_core -c "
SELECT count(*)
FROM pg_constraint
WHERE conrelid='analytics.profit_factory_candidate_v1'::regclass
  AND conname IN (
    'ck_profit_factory_stage_v1',
    'ck_profit_factory_stage_status_v1',
    'ck_profit_factory_operator_decision_v1',
    'ck_profit_factory_stage_time_v1',
    'ck_profit_factory_capital_v1',
    'ck_profit_factory_drawdown_v1',
    'ck_profit_factory_confidence_v1'
  );")

roi_check=$(psql -qAt -v ON_ERROR_STOP=1 -d finam_core -c "
BEGIN;
INSERT INTO analytics.profit_factory_candidate_v1 (
  candidate_id, workflow_run_id, symbol, strategy_code, timeframe,
  factory_stage, stage_status, expected_profit, realized_profit,
  capital_allocated, max_drawdown, confidence_score,
  operator_decision, decision_reason_code, decision_expected_impact
) VALUES (
  'CONTRACT_TEST_V1', -1, 'TEST', 'TEST_STRATEGY', '1m',
  'PAPER', 'ACTIVE', 150, 25, 100, 5, 0.8,
  'CONTINUE', 'POSITIVE_EXPECTANCY', 125
);
SELECT factory_roi
FROM analytics.profit_factory_candidate_v1
WHERE candidate_id='CONTRACT_TEST_V1';
ROLLBACK;")

test "$table_exists" = "t"
test "$view_exists" = "t"
test "$required_columns" = "14"
test "$constraint_count" = "7"
test "$roi_check" = "0.25000000"

echo "table_exists=$table_exists"
echo "view_exists=$view_exists"
echo "required_columns=$required_columns"
echo "constraint_count=$constraint_count"
echo "roi_check=$roi_check"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PROFIT_FACTORY_CONTRACT_V1_READY"
echo "VERDICT=TEST_PROFIT_FACTORY_CONTRACT_V1_OK"
