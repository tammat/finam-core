#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PROFIT_FACTORY_E2E_TEST_CHAIN_V1 ==="

psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/023_profit_factory_identity_contract_v1.sql
psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/024_profit_factory_trust_foundation_v1.sql
psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/027_profit_factory_e2e_test_chain_v1.sql

chain=$(psql -At -F '|' -d finam_core -c "
SELECT i.data_scope, h.handoff_status, a.allocation_status,
       a.capital_allocated, f.expected_profit, f.realized_profit,
       round(f.realized_profit / NULLIF(a.capital_allocated, 0), 6)
FROM analytics.profit_factory_candidate_identity_v1 i
JOIN analytics.profit_factory_runtime_handoff_v1 h USING(candidate_id)
JOIN analytics.profit_factory_production_allocation_v1 a USING(candidate_id, handoff_id)
JOIN analytics.profit_factory_profit_fact_v1 f USING(candidate_id, allocation_id)
WHERE i.candidate_id='11111111-1111-4111-8111-111111111111';")

real_summary_count=$(psql -At -d finam_core -c "
SELECT total_candidates FROM analytics.profit_factory_trust_summary_v1;")
real_identity_count=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.profit_factory_candidate_identity_v1 WHERE data_scope='REAL';")
test_identity_count=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.profit_factory_candidate_identity_v1 WHERE data_scope='TEST';")

test "$chain" = "TEST|ACCEPTED|ACTIVE|100000.000000|12500.000000|8700.000000|0.087000"
test "$real_summary_count" = "$real_identity_count"
test "$test_identity_count" -ge 1

echo "chain=$chain"
echo "real_summary_count=$real_summary_count"
echo "real_identity_count=$real_identity_count"
echo "test_identity_count=$test_identity_count"
echo "test_data_isolated=1"
echo "VERDICT=TEST_PROFIT_FACTORY_E2E_TEST_CHAIN_V1_OK"
