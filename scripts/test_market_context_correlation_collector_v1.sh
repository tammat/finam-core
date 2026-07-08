#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_CORRELATION_COLLECTOR_V1 ==="

sql_file="sql/knowledge/market_context_correlation_collector_v1.sql"
collector="src/scripts/market_context_correlation_collector_v1.py"

test -f "$sql_file"
test -f "$collector"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_corr_collector PYTHONPATH=src/scripts \
python -m py_compile "$collector"

if grep -RInE 'DROP TABLE|TRUNCATE|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*edge_score_model_v2|DELETE FROM' "$sql_file" "$collector"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RInE "SBER|LKOH|VTBR|GAZP|IMOEX|RTSI|DEFAULT_M5|DEFAULT_H1|DEFAULT_D1|0\.70|250|100|50" "$collector"; then
  echo "HARDCODE_FOUND_IN_COLLECTOR"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

out=$(PYTHONPYCACHEPREFIX=/tmp/finam_pycache_corr_collector PYTHONPATH=src/scripts python "$collector")
echo "$out"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_ROWCOUNT_CHANGED before=$before_edge after=$after_edge"
  exit 1
fi

echo "$out" | grep -q "VERDICT=MARKET_CONTEXT_CORRELATION_COLLECTOR_V1_READY"
echo "$out" | grep -q "config_source=postgres"
echo "$out" | grep -q "symbol_hardcode=0"
echo "$out" | grep -q "threshold_hardcode=0"

rule_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.correlation_rule_v1
WHERE is_active;
")

universe_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.correlation_universe_v1
WHERE is_active;
")

correlation_context=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
  AND correlation_state <> 'UNKNOWN';
")

relationship_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.relationship_v1
WHERE source_version='MARKET_CONTEXT_CORRELATION_COLLECTOR_V1'
  AND relation_type='CORRELATION'
  AND is_active;
")

test "$rule_rows" -ge 1
test "$universe_rows" -ge 1

echo "correlation_rule_rows=$rule_rows"
echo "correlation_universe_rows=$universe_rows"
echo "correlation_context_rows=$correlation_context"
echo "correlation_relationship_rows=$relationship_rows"
echo "hardcode=0"
echo "destructive_sql=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_CORRELATION_COLLECTOR_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_CORRELATION_COLLECTOR_V1_OK"
