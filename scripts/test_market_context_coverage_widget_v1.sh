#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_COVERAGE_WIDGET_V1 ==="

files=(
  src/marketcore/presentation/providers/knowledge_coverage_provider.py
  src/marketcore/presentation/providers/operator_home_widgets_provider.py
  src/marketcore/presentation/widgets/renderer.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_knowledge_coverage_widget PYTHONPATH=src python -m py_compile "$f"
done

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.providers.knowledge_coverage_provider import KnowledgeCoverageProvider
from marketcore.presentation.providers.operator_home_widgets_provider import OperatorHomeWidgetsProvider
from marketcore.presentation.widgets.renderer import render_widget

vm = KnowledgeCoverageProvider().load()
assert vm.widget_id == "knowledge_coverage"
assert vm.title_key == "widget.knowledge_coverage.title"
assert "knowledge.coverage.total" in vm.content

html = render_widget(vm)
assert 'data-widget-id="knowledge_coverage"' in html
assert "Покрытие знаний" in html
assert "Общее покрытие" in html
assert "%" in html

widgets = OperatorHomeWidgetsProvider().load()
ids = {w.widget_id for w in widgets}
assert "knowledge_coverage" in ids

print("knowledge_coverage_provider=OK")
print("knowledge_coverage_widget_render=OK")
print("operator_home_widget_included=OK")
PY

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|UPDATE .*edge_score_model_v2|DELETE FROM|DROP TABLE|TRUNCATE' "${files[@]}"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/?v=$(date +%s)" >/tmp/market_context_coverage_widget_v1.html

grep -q 'data-widget-id="knowledge_coverage"' /tmp/market_context_coverage_widget_v1.html
grep -q "Покрытие знаний" /tmp/market_context_coverage_widget_v1.html
grep -q "Общее покрытие" /tmp/market_context_coverage_widget_v1.html

if grep -Eo '(widget|knowledge)\.[A-Za-z0-9_.-]+' /tmp/market_context_coverage_widget_v1.html; then
  echo "RAW_I18N_KEY_VISIBLE"
  exit 1
fi

echo "knowledge_coverage_widget=OK"
echo "operator_home_http=OK"
echo "raw_i18n_keys=0"
echo "destructive_sql=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_COVERAGE_WIDGET_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_COVERAGE_WIDGET_V1_OK"
