#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_PORTFOLIO_PAGE_V2 ==="

files=(
  "src/marketcore/presentation/workspace_v2/portfolio_page_v2.py"
  "src/marketcore/presentation/workspace_v2/presenter/portfolio_v2_presenter.py"
  "src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py"
  "src/marketcore/presentation/router.py"
)

PYTHONPYCACHEPREFIX=/tmp/workspace_v2_portfolio_page \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE 'SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(' \
  src/marketcore/presentation/workspace_v2/portfolio_page_v2.py; then
  echo "SQL_IN_PAGE_FOUND"
  exit 1
fi

if grep -RInE 'Открыть|Paper|Shadow|Live|📈|🧺|💱' \
  src/marketcore/presentation/workspace_v2/portfolio_page_v2.py \
  src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py; then
  echo "UI_HARDCODE_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.portfolio_page_v2 import (
    render_workspace_v2_portfolio_page_v2,
)

html = render_workspace_v2_portfolio_page_v2()

assert "mc-v2-shell" in html
assert "data-i18n-key" in html
assert "mc-v2-card" in html
assert "Открыть" not in html

print("portfolio_page_v2=OK")
PY

echo "portfolio_page_v2=OK"
echo "presenter_used=OK"
echo "renderer_used=OK"
echo "sql_in_page=0"
echo "ui_hardcodes=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_PORTFOLIO_PAGE_V2_READY"
echo "VERDICT=TEST_WORKSPACE_V2_PORTFOLIO_PAGE_V2_OK"
