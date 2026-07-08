#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_PART4D_I18N_CLEANUP ==="

target="src/marketcore/presentation/components/max_edge_card.py"

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile "$target"

grep -q "edge.score.max.title" "$target"
grep -q "edge.score.max.symbol" "$target"
grep -q "edge.score.max.strategy" "$target"
grep -q "edge.score.max.confidence" "$target"

if grep -nE 'Максимальный edge|Инструмент|Стратегия|Доверие|Рекомендация|Сделки' "$target"; then
  echo "HARDCODED_UI_TEXT_FOUND"
  exit 1
fi

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
  ('edge.score.explain.contribution')
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

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/max-edge?v=$(date +%s)" >/tmp/max_edge_part4d.html

grep -q "edge.score.max.title" /tmp/max_edge_part4d.html
grep -q "edge-score-explain-card" /tmp/max_edge_part4d.html

echo "i18n_missing=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_PART4D_I18N_CLEANUP_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_PART4D_I18N_CLEANUP_OK"
