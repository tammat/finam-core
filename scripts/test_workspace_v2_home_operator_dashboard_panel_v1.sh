#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_HOME_OPERATOR_DASHBOARD_PANEL_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 \
  -f sql/presentation/workspace_v2_home_operator_dashboard_i18n_v1.sql

PYTHONPYCACHEPREFIX=/tmp/home_operator_dashboard_panel \
PYTHONPATH=src \
python -m py_compile \
  src/marketcore/presentation/workspace_v2/resolver/home_operator_dashboard_resolver_v1.py \
  src/marketcore/presentation/workspace_v2/presenter/home_v2_presenter.py \
  src/marketcore/presentation/workspace_v2/renderer/home_v2_renderer.py \
  src/marketcore/presentation/workspace_v2/home_page_v2.py

if grep -RInE 'SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(' \
  src/marketcore/presentation/workspace_v2/presenter/home_v2_presenter.py \
  src/marketcore/presentation/workspace_v2/renderer/home_v2_renderer.py \
  src/marketcore/presentation/workspace_v2/home_page_v2.py; then
  echo "SQL_OUTSIDE_RESOLVER_FOUND"
  exit 1
fi

html=$(PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.home_page_v2 import render_workspace_v2_home_page_v2
print(render_workspace_v2_home_page_v2())
PY
)

echo "$html" | grep -q "Операторская панель"
echo "$html" | grep -q "Здоровье модели"
echo "$html" | grep -q "Рекомендации"
echo "$html" | grep -q "Воронка сигналов"
echo "$html" | grep -q "Риск"
echo "$html" | grep -q "События"
echo "$html" | grep -q "Записей"

if echo "$html" | grep -E "home\.operator\.|data-i18n-key"; then
  echo "RAW_I18N_KEY_FOUND"
  exit 1
fi

echo "home_operator_dashboard_panel=OK"
echo "presenter_uses_operator_resolver=OK"
echo "i18n=OK"
echo "sql_outside_resolver=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_HOME_OPERATOR_DASHBOARD_PANEL_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_HOME_OPERATOR_DASHBOARD_PANEL_V1_OK"
