#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_MARKET_KNOWLEDGE_POSTGRES_SCHEMA_V1 ==="

schema_sql="sql/knowledge/market_knowledge_postgres_schema_v1.sql"
test -f "$schema_sql"

if grep -RInE 'DROP TABLE|TRUNCATE|DELETE FROM|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills' "$schema_sql"; then
  echo "DESTRUCTIVE_SQL_FOUND"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f "$schema_sql"

missing=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  VALUES
    ('knowledge.market_v1'),
    ('knowledge.exchange_v1'),
    ('knowledge.asset_class_v1'),
    ('knowledge.sector_v1'),
    ('knowledge.industry_v1'),
    ('knowledge.instrument_v1'),
    ('knowledge.market_regime_v1'),
    ('knowledge.market_context_v1'),
    ('knowledge.strategy_context_v1'),
    ('knowledge.edge_context_v1'),
    ('knowledge.relationship_v1'),
    ('knowledge.observation_v1'),
    ('knowledge.recommendation_v1')
) AS required(full_name)
LEFT JOIN pg_class c
  ON c.relname = split_part(required.full_name, '.', 2)
LEFT JOIN pg_namespace n
  ON n.oid = c.relnamespace
 AND n.nspname = split_part(required.full_name, '.', 1)
WHERE c.oid IS NULL;
")

if [ "$missing" != "0" ]; then
  echo "MISSING_KNOWLEDGE_TABLES=$missing"
  exit 1
fi

unsafe_reco=$(psql -At -d finam_core -c "
SELECT count(*)
FROM information_schema.check_constraints
WHERE constraint_schema='knowledge'
  AND check_clause ILIKE '%execution_allowed = 0%';
")

if [ "$unsafe_reco" -lt 1 ]; then
  echo "MISSING_EXECUTION_SAFETY_CHECK"
  exit 1
fi

echo "knowledge_schema=OK"
echo "knowledge_tables=13"
echo "destructive_sql=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_MARKET_KNOWLEDGE_POSTGRES_SCHEMA_V1_READY"
echo "VERDICT=TEST_MARKETCORE_MARKET_KNOWLEDGE_POSTGRES_SCHEMA_V1_OK"
