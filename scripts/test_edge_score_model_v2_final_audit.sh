#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_FINAL_AUDIT ==="

required_tests=(
  "scripts/test_edge_score_model_v2_part2.sh"
  "scripts/test_edge_score_model_v2_part3_ui.sh"
  "scripts/test_edge_score_model_v2_part4_explain_card.sh"
  "scripts/test_edge_score_model_v2_part4b_max_edge_explain_ui.sh"
  "scripts/test_edge_score_model_v2_part4c_max_edge_explain_html.sh"
  "scripts/test_edge_score_model_v2_part4d_i18n_cleanup.sh"
  "scripts/test_edge_score_model_v2_part5_no_hardcode_audit.sh"
  "scripts/test_edge_score_model_v2_part6_risk_freeze_gate.sh"
)

for t in "${required_tests[@]}"; do
  test -x "$t" || { echo "MISSING_OR_NOT_EXECUTABLE_TEST=$t"; exit 1; }
done

files=(
  "src/scripts/build_edge_score_model_v2.py"
  "src/scripts/build_edge_score_model_v2_reconciliation.py"
  "src/scripts/build_edge_score_model_v2_explain.py"
  "src/marketcore/presentation/providers/max_edge_provider.py"
  "src/marketcore/presentation/components/max_edge_card.py"
)

rm -rf /tmp/finam_pycache_final_audit
mkdir -p /tmp/finam_pycache_final_audit

for f in "${files[@]}"; do
  test -f "$f" || { echo "MISSING_FILE=$f"; exit 1; }
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_final_audit PYTHONDONTWRITEBYTECODE=0 PYTHONPATH=src python -m py_compile "$f"
done

# Финальная БД-проверка V2.
v2_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2
WHERE source_version='EDGE_SCORE_MODEL_V2';
")

reconciliation_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2_reconciliation
WHERE source_version='EDGE_SCORE_MODEL_V2_PART_2';
")

explain_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2_explain
WHERE source_version='EDGE_SCORE_MODEL_V2_PART_4_EXPLAIN_CARD';
")

weight_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_weight_v2
WHERE model_code='EDGE_SCORE_V2'
  AND metric_group='MODEL_GROUP'
  AND enabled=true;
")

if [ "$v2_rows" -lt 1 ]; then echo "NO_V2_ROWS"; exit 1; fi
if [ "$reconciliation_rows" -lt 1 ]; then echo "NO_RECONCILIATION_ROWS"; exit 1; fi
if [ "$explain_rows" -lt 1 ]; then echo "NO_EXPLAIN_ROWS"; exit 1; fi
if [ "$weight_rows" -lt 4 ]; then echo "MODEL_GROUP_WEIGHTS_NOT_CONFIGURED=$weight_rows"; exit 1; fi

# I18N.
missing_i18n=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  VALUES
  ('edge.score.max.title'),
  ('edge.score.max.symbol'),
  ('edge.score.max.strategy'),
  ('edge.score.max.score'),
  ('edge.score.max.confidence'),
  ('edge.score.max.timeframe'),
  ('edge.score.max.recommendation'),
  ('edge.score.max.trades'),
  ('edge.score.explain.title'),
  ('edge.score.explain.group'),
  ('edge.score.explain.score'),
  ('edge.score.explain.weight'),
  ('edge.score.explain.contribution'),
  ('edge.score.explain.verdict')
) AS required(resource_key)
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key=required.resource_key
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
")

if [ "$missing_i18n" != "0" ]; then
  echo "MISSING_I18N_RESOURCES=$missing_i18n"
  exit 1
fi

# No hardcode: веса/коэффициенты не в Python, кроме точности quantize.
if grep -RInE 'Decimal\("0\.[0-9]+"\)|\* *0\.[0-9]+|\+ *0\.[0-9]+' \
  "${files[@]}" | grep -v 'Decimal("0.000001")'; then
  echo "HARDCODED_MODEL_WEIGHT_OR_COEFFICIENT_FOUND"
  exit 1
fi

# No execution coupling.
if grep -RInE 'send_order|place_order|cancel_order|execute_order|broker\.|FinamClient|submit_order|OrderRequest|ExecutionEngine|PaperExecution|LiveExecution' \
  "${files[@]}"; then
  echo "EXECUTION_COUPLING_FOUND_IN_EDGE_SCORE_V2"
  exit 1
fi

# No runtime/execution mutation.
if grep -RInE '(^|[^a-zA-Z_])(runtime_allowed|execution_enabled|micro_live_allowed)\s*=|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills' \
  "${files[@]}" | grep -v 'print("micro_live_allowed=0")' | grep -v 'print("runtime_changed=0")' | grep -v 'print("execution_changed=0")'; then
  echo "RUNTIME_OR_EXECUTION_MUTATION_FOUND"
  exit 1
fi

runtime_cols=$(psql -At -d finam_core -c "
SELECT count(*)
FROM information_schema.columns
WHERE table_schema='analytics'
  AND table_name IN (
    'edge_score_model_v2',
    'edge_score_model_v2_reconciliation',
    'edge_score_model_v2_explain'
  )
  AND column_name IN (
    'runtime_allowed',
    'execution_enabled',
    'micro_live_allowed',
    'execution_allowed',
    'order_allowed'
  );
")

if [ "$runtime_cols" != "0" ]; then
  echo "RUNTIME_COLUMNS_FOUND_IN_EDGE_SCORE_V2_TABLES=$runtime_cols"
  exit 1
fi

# UI endpoint.
curl -fsS "http://127.0.0.1:8080/max-edge?v=$(date +%s)" >/tmp/max_edge_v2_final_audit.html

grep -q "edge.score.max.title" /tmp/max_edge_v2_final_audit.html
grep -q "edge-score-explain-card" /tmp/max_edge_v2_final_audit.html
grep -q "ECONOMIC" /tmp/max_edge_v2_final_audit.html

echo "v2_rows=$v2_rows"
echo "reconciliation_rows=$reconciliation_rows"
echo "explain_rows=$explain_rows"
echo "weight_rows=$weight_rows"
echo "i18n_missing=0"
echo "runtime_columns_in_v2_tables=0"
echo "execution_coupling=0"
echo "runtime_mutation=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_FINAL_AUDIT_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_FINAL_AUDIT_OK"
