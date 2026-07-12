#!/usr/bin/env bash
set -euo pipefail

psql -v ON_ERROR_STOP=1 -d finam_core -f sql/presentation/031_portfolio_statusbar_i18n_v1.sql
PYTHONPYCACHEPREFIX=/tmp/portfolio_statusbar_pycache PYTHONPATH=src .venv/bin/python -m py_compile \
  src/marketcore/presentation/workspace_v2/presenter/portfolio_v2_presenter.py \
  src/marketcore/presentation/workspace_v2/portfolio_page_v2.py \
  src/marketcore/presentation/services/operator_settings_v1.py \
  src/marketcore/presentation/services/moex_index_service_v1.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python - <<'PY' >/tmp/portfolio_statusbar_v1.html
from marketcore.presentation.workspace_v2.portfolio_page_v2 import render_workspace_v2_portfolio_page_v2
print(render_workspace_v2_portfolio_page_v2())
PY

grep -q '<!doctype html>' /tmp/portfolio_statusbar_v1.html
grep -q 'runtime.css' /tmp/portfolio_statusbar_v1.html
grep -q 'data-section="ALERTS"' /tmp/portfolio_statusbar_v1.html
grep -q '>ONLINE<' /tmp/portfolio_statusbar_v1.html
grep -q '>REAL<' /tmp/portfolio_statusbar_v1.html
grep -q '>Europe/Moscow<' /tmp/portfolio_statusbar_v1.html
grep -q '>RUB<' /tmp/portfolio_statusbar_v1.html
grep -q '>Finam<' /tmp/portfolio_statusbar_v1.html
grep -Eq '[0-9]{2}\.[0-9]{2}\.[0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2}' /tmp/portfolio_statusbar_v1.html
grep -q 'Индекс MOEX' /tmp/portfolio_statusbar_v1.html
grep -q 'К пред. дню' /tmp/portfolio_statusbar_v1.html
grep -q 'portfolio.statusbar' src/marketcore/presentation/workspace_v2/presenter/portfolio_v2_presenter.py
echo 'VERDICT=TEST_PORTFOLIO_STATUSBAR_V1_OK'
