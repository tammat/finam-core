#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_PART6_RISK_FREEZE_GATE ==="

files=(
  "src/scripts/build_edge_score_model_v2.py"
  "src/scripts/build_edge_score_model_v2_reconciliation.py"
  "src/scripts/build_edge_score_model_v2_explain.py"
  "src/marketcore/presentation/providers/max_edge_provider.py"
  "src/marketcore/presentation/components/max_edge_card.py"
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_part6 PYTHONDONTWRITEBYTECODE=0 PYTHONPATH=src python -m py_compile "$f"
done

# 1. Запрещаем любые признаки отправки заявок/исполнения в V2-файлах.
if grep -RInE 'send_order|place_order|cancel_order|execute_order|broker\.|FinamClient|submit_order|OrderRequest|ExecutionEngine|PaperExecution|LiveExecution' \
  "${files[@]}"; then
  echo "EXECUTION_COUPLING_FOUND_IN_EDGE_SCORE_V2"
  exit 1
fi

# 2. Запрещаем изменение runtime/execution flags в V2-файлах.
if grep -RInE '(^|[^a-zA-Z_])(runtime_allowed|execution_enabled|micro_live_allowed)\s*=|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills' \
  "${files[@]}" | grep -v 'print("micro_live_allowed=0")' | grep -v 'print("runtime_changed=0")' | grep -v 'print("execution_changed=0")'; then
  echo "RUNTIME_OR_EXECUTION_MUTATION_FOUND"
  exit 1
fi

# 3. Проверяем, что V2 analytics tables не содержат разрешения runtime/execution.
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

# 4. Проверяем, что V2/explain таблицы заполнены, но являются аналитическими.
v2_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2
WHERE source_version='EDGE_SCORE_MODEL_V2';
")

explain_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2_explain
WHERE source_version='EDGE_SCORE_MODEL_V2_PART_4_EXPLAIN_CARD';
")

if [ "$v2_rows" -lt 1 ]; then
  echo "NO_EDGE_SCORE_V2_ROWS"
  exit 1
fi

if [ "$explain_rows" -lt 1 ]; then
  echo "NO_EDGE_SCORE_EXPLAIN_ROWS"
  exit 1
fi

# 5. Проверяем UI read-only доступность.
curl -fsS "http://127.0.0.1:8080/max-edge?v=$(date +%s)" >/tmp/max_edge_part6_gate.html

grep -q "edge.score.max.title" /tmp/max_edge_part6_gate.html
grep -q "edge-score-explain-card" /tmp/max_edge_part6_gate.html

# 6. Фиксируем freeze verdict.
echo "v2_rows=$v2_rows"
echo "explain_rows=$explain_rows"
echo "runtime_columns_in_v2_tables=0"
echo "execution_coupling=0"
echo "runtime_mutation=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_PART_6_RISK_FREEZE_GATE_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_PART6_RISK_FREEZE_GATE_OK"
