#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_PART4_EXPLAIN_CARD ==="

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_score_model_v2_explain.py

out=$(PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python src/scripts/build_edge_score_model_v2_explain.py)
echo "$out"

echo "$out" | grep -q "runtime_changed=0"
echo "$out" | grep -q "execution_changed=0"
echo "$out" | grep -q "orders_changed=0"
echo "$out" | grep -q "fills_changed=0"
echo "$out" | grep -q "micro_live_allowed=0"
echo "$out" | grep -q "VERDICT=EDGE_SCORE_MODEL_V2_PART_4_EXPLAIN_CARD_READY"

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2_explain
WHERE source_version='EDGE_SCORE_MODEL_V2_PART_4_EXPLAIN_CARD';
")

if [ "$rows" -lt 1 ]; then
  echo "NO_EXPLAIN_ROWS"
  exit 1
fi

missing_i18n=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  VALUES
  ('edge.score.explain.title'),
  ('edge.score.explain.total'),
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

grep -RniE 'Decimal\("0\.[0-9]+"\)|"Экономика"|"Надежность"|"Исполнение"|"Риск"|"Итоговый score"|"Вклад"' \
  src/scripts/build_edge_score_model_v2_explain.py && {
    echo "HARDCODE_FOUND_IN_PART4"
    exit 1
  } || true

echo "explain_rows=$rows"
echo "i18n_missing=0"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_PART4_EXPLAIN_CARD_OK"
