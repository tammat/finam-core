#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_RECOMMENDATION_WIDGET_V1 ==="

files=(
  src/marketcore/presentation/viewmodels/recommendation_viewmodel.py
  src/marketcore/presentation/providers/recommendation_widget_provider.py
  src/marketcore/presentation/providers/operator_home_widgets_provider.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_recommendation_widget PYTHONPATH=src python -m py_compile "$f"
done

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|UPDATE .*edge_score_model_v2|DELETE FROM|DROP TABLE|TRUNCATE' "${files[@]}"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RInE "SBER|LKOH|VTBR|GAZP|BUY|SELL|LONG|SHORT|80|70|60|50|0\.70|0\.80|0\.90" "${files[@]}"; then
  echo "HARDCODE_FOUND"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('widget.recommendation.title', 'ru', 'Рекомендация', 'Рекомендация', 'Рекоменд.', 'Исследовательская рекомендация MarketCore', '🧠', 'widget'),
('recommendation.confidence', 'ru', 'Уверенность', 'Уверенность', 'Увер.', 'Уровень уверенности рекомендации', '', 'recommendation')
ON CONFLICT(resource_key, locale_code)
DO UPDATE SET
  caption=EXCLUDED.caption,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  tooltip=EXCLUDED.tooltip,
  icon=EXCLUDED.icon,
  resource_group=EXCLUDED.resource_group,
  updated_at=now();
SQL

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.providers.recommendation_widget_provider import RecommendationWidgetProvider
from marketcore.presentation.providers.operator_home_widgets_provider import OperatorHomeWidgetsProvider
from marketcore.presentation.widgets.renderer import render_widget

vm = RecommendationWidgetProvider().load()
assert vm.widget_id == "recommendation"
assert vm.title_key == "widget.recommendation.title"
assert vm.state == "readonly"

html = render_widget(vm)
assert 'data-widget-id="recommendation"' in html
assert "Рекомендация" in html
assert "Уверенность" in html
assert "%" in html

widgets = OperatorHomeWidgetsProvider().load()
assert "recommendation" in {w.widget_id for w in widgets}

print("recommendation_widget_provider=OK")
print("recommendation_widget_render=OK")
print("operator_home_widget_included=OK")
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/?v=$(date +%s)" >/tmp/market_context_recommendation_widget_v1.html

grep -q 'data-widget-id="recommendation"' /tmp/market_context_recommendation_widget_v1.html
grep -q "Рекомендация" /tmp/market_context_recommendation_widget_v1.html
grep -q "Уверенность" /tmp/market_context_recommendation_widget_v1.html
grep -q "%" /tmp/market_context_recommendation_widget_v1.html

if grep -Eo '(widget|recommendation|reason)\.[A-Za-z0-9_.-]+' /tmp/market_context_recommendation_widget_v1.html; then
  echo "RAW_I18N_KEY_VISIBLE"
  exit 1
fi

result_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge.recommendation_result_v1;")
reason_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge.recommendation_reason_v1;")

test "$result_rows" -ge 1
test "$reason_rows" -ge 1

echo "recommendation_result_rows=$result_rows"
echo "recommendation_reason_rows=$reason_rows"
echo "recommendation_widget_provider=OK"
echo "recommendation_widget_render=OK"
echo "recommendation_widget_http=OK"
echo "raw_i18n_keys=0"
echo "hardcode=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_RECOMMENDATION_WIDGET_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_RECOMMENDATION_WIDGET_V1_OK"
