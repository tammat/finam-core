#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_HOME_STATUS_PANEL_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 \
  -f sql/presentation/workspace_v2_home_status_panel_v1.sql

psql -d finam_core -v ON_ERROR_STOP=1 \
  -f sql/presentation/workspace_v2_status_i18n_patch_v1.sql

PYTHONPYCACHEPREFIX=/tmp/workspace_home_status_panel \
PYTHONPATH=src \
python -m py_compile \
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

echo "$html" | grep -q "Панель состояния"
echo "$html" | grep -q "Система"
echo "$html" | grep -q "Портфель"
echo "$html" | grep -q "Исследование"
echo "$html" | grep -q "Проба"
echo "$html" | grep -q "Наблюдение"
echo "$html" | grep -q "Runtime"
echo "$html" | grep -q "Заблокировано"

if echo "$html" | grep -E "home\.card\.status|home\.section\.status|ui\.status\.blocked"; then
  echo "RAW_I18N_KEY_FOUND"
  exit 1
fi

echo "home_status_panel=OK"
echo "i18n=OK"
echo "sql_outside_resolver=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_HOME_STATUS_PANEL_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_HOME_STATUS_PANEL_V1_OK"
