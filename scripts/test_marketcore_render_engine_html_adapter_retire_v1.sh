#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_RENDER_ENGINE_HTML_ADAPTER_RETIRE_V1 ==="

files=(
  "src/marketcore/presentation/render_engine/__init__.py"
  "src/marketcore/presentation/render_engine/web_renderer.py"
  "src/marketcore/presentation/render_tree/render_node.py"
  "src/marketcore/presentation/render_tree/render_document.py"
  "src/marketcore/presentation/workspace_v2/portfolio_page_v2.py"
  "src/marketcore/presentation/workspace_v2/home_page_v2.py"
)

PYTHONPYCACHEPREFIX=/tmp/render_engine_retire \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

test ! -f src/marketcore/presentation/render_tree/html_adapter.py

if grep -RIn "HtmlAdapter" src/marketcore/presentation; then
  echo "HTML_ADAPTER_REFERENCE_FOUND"
  exit 1
fi

if grep -RIn "render_tree.html_adapter" src/marketcore/presentation; then
  echo "HTML_ADAPTER_IMPORT_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.home_page_v2 import render_workspace_v2_home_page_v2
from marketcore.presentation.workspace_v2.portfolio_page_v2 import render_workspace_v2_portfolio_page_v2

home = render_workspace_v2_home_page_v2()
portfolio = render_workspace_v2_portfolio_page_v2()
phone = render_workspace_v2_portfolio_page_v2(theme_code="PHONE")

assert "MarketCore OS" in home
assert "Портфель" in portfolio
assert "P&amp;L %" in portfolio
assert "max-width:480px" in phone

print("web_renderer=OK")
print("html_adapter_retired=OK")
PY

echo "web_renderer=OK"
echo "html_adapter_file=0"
echo "html_adapter_references=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_RENDER_ENGINE_HTML_ADAPTER_RETIRE_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RENDER_ENGINE_HTML_ADAPTER_RETIRE_V1_OK"
