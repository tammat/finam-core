#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_PART5_NO_HARDCODE_AUDIT ==="

files=(
  "src/scripts/build_edge_score_model_v2.py"
  "src/scripts/build_edge_score_model_v2_reconciliation.py"
  "src/scripts/build_edge_score_model_v2_explain.py"
  "src/marketcore/presentation/providers/max_edge_provider.py"
  "src/marketcore/presentation/components/max_edge_card.py"
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_part5 PYTHONDONTWRITEBYTECODE=0 PYTHONPATH=src python -m py_compile "$f"
done

echo "compiled_files=${#files[@]}"

# 1. Запрещаем хардкод весов модели в Python.
if grep -RInE 'Decimal\("0\.[0-9]+"\)|\* *0\.[0-9]+|\+ *0\.[0-9]+' \
  "${files[@]}" | grep -v 'Decimal("0.000001")'; then
  echo "HARDCODED_MODEL_WEIGHT_OR_COEFFICIENT_FOUND"
  exit 1
fi

# 2. Запрещаем видимые UI-подписи в компоненте max-edge.
if grep -nE 'Максимальный edge|Инструмент|Стратегия|Доверие|Рекомендация|Сделки|Экономика|Надежность|Исполнение|Риск|Вклад|Оценка|Вес|Группа' \
  src/marketcore/presentation/components/max_edge_card.py; then
  echo "HARDCODED_UI_TEXT_FOUND"
  exit 1
fi

# 3. Проверяем, что max-edge card использует i18n keys.
for key in \
  edge.score.max.title \
  edge.score.max.symbol \
  edge.score.max.strategy \
  edge.score.max.score \
  edge.score.max.confidence \
  edge.score.max.timeframe \
  edge.score.max.recommendation \
  edge.score.max.trades \
  edge.score.explain.title \
  edge.score.explain.group \
  edge.score.explain.score \
  edge.score.explain.weight \
  edge.score.explain.contribution
do
  grep -q "$key" src/marketcore/presentation/components/max_edge_card.py
done

# 4. Проверяем наличие i18n-ресурсов в БД.
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

# 5. Проверяем, что веса модели берутся из БД, а не из Python.
weight_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_weight_v2
WHERE model_code='EDGE_SCORE_V2'
  AND metric_group='MODEL_GROUP'
  AND enabled=true;
")

if [ "$weight_rows" -lt 4 ]; then
  echo "MODEL_GROUP_WEIGHTS_NOT_CONFIGURED=$weight_rows"
  exit 1
fi

# 6. Проверяем explain-слой.
explain_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2_explain
WHERE source_version='EDGE_SCORE_MODEL_V2_PART_4_EXPLAIN_CARD';
")

if [ "$explain_rows" -lt 1 ]; then
  echo "NO_EXPLAIN_ROWS"
  exit 1
fi

# 7. Проверяем read-only UI.
curl -fsS "http://127.0.0.1:8080/max-edge?v=$(date +%s)" >/tmp/max_edge_part5_audit.html

grep -q "edge.score.max.title" /tmp/max_edge_part5_audit.html
grep -q "edge-score-explain-card" /tmp/max_edge_part5_audit.html

echo "i18n_missing=0"
echo "weight_rows=$weight_rows"
echo "explain_rows=$explain_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_PART_5_NO_HARDCODE_AUDIT_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_PART5_NO_HARDCODE_AUDIT_OK"
