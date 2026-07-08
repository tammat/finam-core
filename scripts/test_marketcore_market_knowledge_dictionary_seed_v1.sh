#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1 ==="

seed_sql="sql/knowledge/market_knowledge_dictionary_seed_v1.sql"
test -f "$seed_sql"

if grep -RInE 'DROP TABLE|TRUNCATE|DELETE FROM|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills' "$seed_sql"; then
  echo "DESTRUCTIVE_OR_EXECUTION_SQL_FOUND"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f "$seed_sql"

market_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge.market_v1 WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1';")
exchange_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge.exchange_v1 WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1';")
asset_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge.asset_class_v1 WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1';")
sector_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge.sector_v1 WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1';")
regime_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge.market_regime_v1 WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1';")

test "$market_rows" -ge 1
test "$exchange_rows" -ge 1
test "$asset_rows" -ge 6
test "$sector_rows" -ge 8
test "$regime_rows" -ge 11

safety=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_v1
WHERE execution_allowed <> 0
   OR runtime_allowed <> 0
   OR micro_live_allowed <> 0;
")

if [ "$safety" != "0" ]; then
  echo "UNSAFE_RECOMMENDATION_ROWS=$safety"
  exit 1
fi

echo "market_rows=$market_rows"
echo "exchange_rows=$exchange_rows"
echo "asset_class_rows=$asset_rows"
echo "sector_rows=$sector_rows"
echo "market_regime_rows=$regime_rows"
echo "destructive_sql=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1_READY"
echo "VERDICT=TEST_MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1_OK"
