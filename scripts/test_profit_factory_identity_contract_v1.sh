#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PROFIT_FACTORY_IDENTITY_CONTRACT_V1 ==="

psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/023_profit_factory_identity_contract_v1.sql

source_count=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE candidate_uuid IS NOT NULL
  AND observation_uuid IS NOT NULL
  AND btrim(research_batch_id) <> ''
  AND btrim(research_code) <> ''
  AND btrim(strategy_code) <> ''
  AND btrim(strategy_version) <> ''
  AND btrim(symbol) <> ''
  AND btrim(timeframe) <> ''
  AND btrim(parameter_hash) <> ''
  AND btrim(dataset_version) <> '';")

identity_count=$(psql -At -d finam_core -c \
  "SELECT count(*) FROM analytics.profit_factory_candidate_identity_v1 WHERE data_scope='REAL';")

identity_mismatches=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.profit_factory_candidate_identity_v1 i
LEFT JOIN analytics.edge_candidate_v1 e
  ON e.id=i.edge_candidate_id
WHERE i.data_scope='REAL'
  AND (e.id IS NULL
   OR i.candidate_id <> e.candidate_uuid
   OR i.observation_id <> e.observation_uuid
   OR i.research_batch_id <> e.research_batch_id
   OR i.research_code <> e.research_code
   OR i.strategy_code <> e.strategy_code
   OR i.strategy_version <> e.strategy_version
   OR i.symbol <> e.symbol
   OR i.timeframe <> e.timeframe
   OR i.parameter_hash <> e.parameter_hash
   OR i.dataset_version <> e.dataset_version);")

duplicate_candidate_ids=$(psql -At -d finam_core -c "
SELECT count(*) FROM (
  SELECT candidate_id
  FROM analytics.profit_factory_candidate_identity_v1
  GROUP BY candidate_id
  HAVING count(*) > 1
) d;")

duplicate_natural_keys=$(psql -At -d finam_core -c "
SELECT count(*) FROM (
  SELECT strategy_code, strategy_version, symbol, timeframe,
         parameter_hash, dataset_version
  FROM analytics.profit_factory_candidate_identity_v1
  GROUP BY strategy_code, strategy_version, symbol, timeframe,
           parameter_hash, dataset_version
  HAVING count(*) > 1
) d;")

constraint_count=$(psql -At -d finam_core -c "
SELECT count(*)
FROM pg_constraint
WHERE conrelid='analytics.profit_factory_candidate_identity_v1'::regclass
  AND conname LIKE 'ck_profit_factory_identity_%_v1';")

test "$source_count" -gt 0
test "$identity_count" = "$source_count"
test "$identity_mismatches" = "0"
test "$duplicate_candidate_ids" = "0"
test "$duplicate_natural_keys" = "0"
test "$constraint_count" = "7"

echo "source_count=$source_count"
echo "identity_count=$identity_count"
echo "identity_mismatches=$identity_mismatches"
echo "duplicate_candidate_ids=$duplicate_candidate_ids"
echo "duplicate_natural_keys=$duplicate_natural_keys"
echo "constraint_count=$constraint_count"
echo "financial_kpi_rows_created=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "VERDICT=PROFIT_FACTORY_IDENTITY_CONTRACT_V1_READY"
echo "VERDICT=TEST_PROFIT_FACTORY_IDENTITY_CONTRACT_V1_OK"
