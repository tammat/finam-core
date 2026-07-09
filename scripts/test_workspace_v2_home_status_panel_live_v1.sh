#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_HOME_STATUS_PANEL_LIVE_V1 ==="

PYTHONPYCACHEPREFIX=/tmp/home_status_live \
PYTHONPATH=src \
python -m py_compile \
src/marketcore/presentation/workspace_v2/domain/home_status_model_v1.py \
src/marketcore/presentation/workspace_v2/resolver/home_status_resolver_v1.py \
src/marketcore/presentation/workspace_v2/presenter/home_v2_presenter.py

html=$(PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.home_page_v2 import render_workspace_v2_home_page_v2
print(render_workspace_v2_home_page_v2())
PY
)

echo "$html" | grep -q "Записей"

echo "$html" | grep -q "Последнее обновление"

echo "home_status_live=OK"

echo "VERDICT=WORKSPACE_V2_HOME_STATUS_PANEL_LIVE_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_HOME_STATUS_PANEL_LIVE_V1_OK"
