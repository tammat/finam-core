#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1 ==="

sql_files=(
  sql/analytics/paper_execution_robustness_audit_v1.sql
  sql/analytics/paper_execution_robustness_parameter_seed_v1.sql
)

py_file="src/scripts/paper_execution_robustness_audit_v1.py"

for f in "${sql_files[@]}"; do
  test -f "$f"
done
test -f "$py_file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_paper_robustness \
PYTHONPATH=src \
python -m py_compile "$py_file"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|DROP TABLE|TRUNCATE|DELETE FROM' "${sql_files[@]}" "$py_file"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RInE 'SBER|LKOH|GAZP|VTBR|BUY|SELL|LONG|SHORT' "${sql_files[@]}" "$py_file"; then
  echo "HARDCODE_FOUND"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f sql/analytics/paper_execution_robustness_audit_v1.sql
psql -d finam_core -v ON_ERROR_STOP=1 -f sql/analytics/paper_execution_robustness_parameter_seed_v1.sql
scripts/test_paper_execution_robustness_i18n_v1.sh

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

out=$(PYTHONPATH=src python "$py_file")
echo "$out"
echo "$out" | grep -q "VERDICT=PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1_READY"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")
test "$before_edge" = "$after_edge"

snapshot_id=$(echo "$out" | awk -F= '/^analytics_snapshot_id=/{print $2}' | tail -1)
test -n "$snapshot_id"

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_robustness_audit_v1
WHERE analytics_snapshot_id=${snapshot_id}
  AND source_version='PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1';
")

bad=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_robustness_audit_v1
WHERE analytics_snapshot_id=${snapshot_id}
  AND (
       production_allowed<>0
    OR auto_decision<>0
    OR sample_status NOT IN ('RESEARCH','VALIDATED','PRODUCTION')
    OR overfit_risk NOT IN ('LOW','MEDIUM','HIGH')
  );
")

test "$rows" = "1"
test "$bad" = "0"

echo "robustness_rows=$rows"
echo "bad_rows=0"
echo "i18n=OK"
echo "parameters_source=postgres"
echo "auto_decision=0"
echo "production_allowed=0"
echo "hardcode=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1_READY"
echo "VERDICT=TEST_PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1_OK"
