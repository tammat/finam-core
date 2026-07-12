#!/usr/bin/env bash
set -euo pipefail

node --check src/marketcore/presentation/ui_runtime/assets/v1/portfolio_workspace_v1.js
PYTHONPYCACHEPREFIX=/tmp/portfolio_interactions_pycache PYTHONPATH=src .venv/bin/python -m py_compile \
  src/marketcore/presentation/ui_runtime/asset_delivery_v1.py \
  src/marketcore/presentation/workspace_v2/portfolio_page_v2.py \
  src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py \
  src/marketcore/presentation/services/operator_settings_v1.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python - <<'PY'
from marketcore.presentation.ui_runtime.asset_delivery_v1 import load_ui_runtime_asset_v1
from marketcore.presentation.workspace_v2.portfolio_page_v2 import render_workspace_v2_portfolio_page_v2

asset = load_ui_runtime_asset_v1('/assets/marketcore/ui-runtime/v1/portfolio-workspace.js')
assert asset.status_code == 200
assert asset.content_type == 'application/javascript; charset=utf-8'
page = render_workspace_v2_portfolio_page_v2()
assert '/portfolio-workspace.js' in page
custom = render_workspace_v2_portfolio_page_v2(timezone='UTC', currency='USD', broker='T-Bank')
assert 'data-timezone="UTC"' in custom
assert 'data-currency="USD"' in custom
assert 'data-broker="T-Bank"' in custom
PY

grep -q 'data-control="search"' src/marketcore/presentation/ui_runtime/assets/v1/portfolio_workspace_v1.js
grep -q 'value="pnl_asc"' src/marketcore/presentation/ui_runtime/assets/v1/portfolio_workspace_v1.js
grep -q 'marketcore.portfolio.density' src/marketcore/presentation/ui_runtime/assets/v1/portfolio_workspace_v1.js
grep -q 'data-control="settings"' src/marketcore/presentation/ui_runtime/assets/v1/portfolio_workspace_v1.js
grep -q 'data-settings="apply"' src/marketcore/presentation/ui_runtime/assets/v1/portfolio_workspace_v1.js
echo 'VERDICT=TEST_PORTFOLIO_WORKSPACE_INTERACTIONS_V1_OK'
