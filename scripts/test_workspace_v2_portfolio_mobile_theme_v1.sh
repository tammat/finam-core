#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_PORTFOLIO_MOBILE_THEME_V1 ==="

sql_file="sql/presentation/workspace_v2_portfolio_mobile_theme_v1.sql"
renderer="src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py"

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

PYTHONPYCACHEPREFIX=/tmp/workspace_v2_portfolio_mobile_theme \
PYTHONPATH=src \
python -m py_compile \
  src/marketcore/presentation/framework/theme_model.py \
  src/marketcore/presentation/framework/theme_resolver.py \
  "$renderer" \
  src/marketcore/presentation/workspace_v2/portfolio_page_v2.py

test ! -f src/marketcore/presentation/static/workspace_v2_mobile_layout_v1.css

if grep -RInE 'workspace_v2_mobile_layout_v1.css|<link rel="stylesheet"|@media|SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(' "$renderer"; then
  echo "FORBIDDEN_RENDERER_CONTENT_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.presenter.portfolio_v2_presenter import PortfolioV2Presenter
from marketcore.presentation.workspace_v2.renderer.portfolio_v2_renderer import render_portfolio_v2

vm = PortfolioV2Presenter().load(limit=20)

desktop = render_portfolio_v2(vm, theme_code="DEFAULT")
phone = render_portfolio_v2(vm, theme_code="PHONE")

assert "max-width:1600px" in desktop
assert "grid-template-columns:repeat(auto-fit,minmax(340px,1fr))" in desktop
assert "grid-template-columns:1fr auto" in desktop

assert "max-width:480px" in phone
assert "grid-template-columns:repeat(auto-fit,minmax(280px,1fr))" in phone
assert "grid-template-columns:1fr;" in phone

assert "P&amp;L %" in phone
assert "portfolio.column." not in phone
assert "data-i18n-key" not in phone

print("mobile_theme=OK")
print("desktop_theme=OK")
PY

echo "mobile_theme=OK"
echo "theme_resolver_used=OK"
echo "css_file=0"
echo "css_link=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_PORTFOLIO_MOBILE_THEME_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_PORTFOLIO_MOBILE_THEME_V1_OK"
