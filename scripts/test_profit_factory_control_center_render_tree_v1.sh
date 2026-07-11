#!/usr/bin/env bash
set -euo pipefail
psql -v ON_ERROR_STOP=1 -d finam_core -f sql/presentation/030_profit_factory_control_center_i18n_v1.sql
PYTHONPYCACHEPREFIX=/tmp/profit_control_center_pycache PYTHONPATH=src .venv/bin/python -m py_compile \
 src/marketcore/presentation/workspace_v2/resolver/profit_factory_control_center_resolver_v1.py \
 src/marketcore/presentation/workspace_v2/presenter/home_v2_presenter.py \
 src/marketcore/presentation/workspace_v2/renderer/home_v2_renderer.py
MARKETCORE_PROFIT_SCOPE=TEST PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python - <<'PY' >/tmp/profit_control_center_tree.json
from marketcore.presentation.workspace_v2.render_tree_http_v1 import home_render_tree_http_v1
print(home_render_tree_http_v1().body.decode())
PY
grep -q 'Центр управления прибылью' /tmp/profit_control_center_tree.json
grep -q '12 500 ₽' /tmp/profit_control_center_tree.json
grep -q '8 700 ₽' /tmp/profit_control_center_tree.json
grep -q '3 800 ₽' /tmp/profit_control_center_tree.json
grep -q '8.7%' /tmp/profit_control_center_tree.json
grep -q 'Прибыль ниже ожидания' /tmp/profit_control_center_tree.json
grep -q 'VERIFIED' /tmp/profit_control_center_tree.json
echo 'VERDICT=TEST_PROFIT_FACTORY_CONTROL_CENTER_RENDER_TREE_V1_OK'
