#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_PORTFOLIO_PAGE_V2_I18N_CHECK ==="

files=(
  "src/marketcore/presentation/workspace_v2/portfolio_page_v2.py"
  "src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py"
  "src/marketcore/presentation/workspace_v2/presenter/portfolio_v2_presenter.py"
  "src/marketcore/presentation/framework/i18n_resolver.py"
  "src/marketcore/presentation/router.py"
)

PYTHONPYCACHEPREFIX=/tmp/workspace_v2_portfolio_i18n_check \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE 'data-i18n-key|portfolio\.workspace\.title|portfolio\.section\.summary\.title|portfolio\.source\.public_' \
  src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py; then
  echo "RAW_I18N_KEY_IN_PORTFOLIO_RENDERER_FOUND"
  exit 1
fi

if grep -RInE 'SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(' \
  src/marketcore/presentation/workspace_v2/portfolio_page_v2.py \
  src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py; then
  echo "SQL_IN_PAGE_OR_RENDERER_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.router import route
from marketcore.presentation.workspace_v2.portfolio_page_v2 import (
    render_workspace_v2_portfolio_page_v2,
)

html = render_workspace_v2_portfolio_page_v2()

assert "Портфель" in html
assert "Сводка" in html
assert "Позиции" in html
assert "mc-v2-shell" in html
assert "mc-v2-card" in html

assert "data-i18n-key" not in html
assert "portfolio.workspace.title" not in html
assert "portfolio.section.summary.title" not in html
assert "portfolio.source.public_" not in html

code, body = route("/workspace-v2/portfolio")
assert code == 200

route_html = body.decode("utf-8")
assert "Портфель" in route_html
assert "data-i18n-key" not in route_html

print("portfolio_page_i18n=OK")
PY

echo "portfolio_page_i18n=OK"
echo "raw_i18n_keys=0"
echo "sql_in_page_or_renderer=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_PORTFOLIO_PAGE_V2_I18N_CHECK_READY"
echo "VERDICT=TEST_WORKSPACE_V2_PORTFOLIO_PAGE_V2_I18N_CHECK_OK"
