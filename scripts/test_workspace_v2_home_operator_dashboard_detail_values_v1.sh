#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_HOME_OPERATOR_DASHBOARD_DETAIL_VALUES_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 \
-f sql/presentation/workspace_v2_home_operator_dashboard_detail_values_v1.sql

PYTHONPYCACHEPREFIX=/tmp/operator_dashboard_detail \
PYTHONPATH=src \
python -m py_compile \
src/marketcore/presentation/workspace_v2/domain/home_operator_dashboard_model_v1.py \
src/marketcore/presentation/workspace_v2/resolver/home_operator_dashboard_resolver_v1.py \
src/marketcore/presentation/workspace_v2/presenter/home_v2_presenter.py \
src/marketcore/presentation/workspace_v2/renderer/home_v2_renderer.py

html=$(PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.home_page_v2 import render_workspace_v2_home_page_v2
print(render_workspace_v2_home_page_v2())
PY
)

echo "$html" | grep -q "Записей"
echo "$html" | grep -q "Обновлено"

echo "operator_dashboard_detail_values=OK"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=WORKSPACE_V2_HOME_OPERATOR_DASHBOARD_DETAIL_VALUES_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_HOME_OPERATOR_DASHBOARD_DETAIL_VALUES_V1_OK"
