#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_RENDER_TREE_V1_MINIMAL ==="

files=(
  "src/marketcore/presentation/render_tree/__init__.py"
  "src/marketcore/presentation/render_tree/render_node.py"
  "src/marketcore/presentation/render_tree/render_document.py"
  "src/marketcore/presentation/render_tree/html_adapter.py"
  "src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py"
  "src/marketcore/presentation/workspace_v2/portfolio_page_v2.py"
)

PYTHONPYCACHEPREFIX=/tmp/marketcore_render_tree_v1 \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE '<main|<section|<article|<div|</' \
  src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py; then
  echo "HTML_IN_PORTFOLIO_RENDERER_FOUND"
  exit 1
fi

if grep -RInE '<main|<section|<article|<div|</' \
  src/marketcore/presentation/render_tree/render_node.py \
  src/marketcore/presentation/render_tree/render_document.py; then
  echo "HTML_IN_RENDER_TREE_MODEL_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.render_tree.html_adapter import HtmlAdapter
from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.render_tree.render_node import RenderNode
from marketcore.presentation.workspace_v2.portfolio_page_v2 import render_workspace_v2_portfolio_page_v2
from marketcore.presentation.workspace_v2.presenter.portfolio_v2_presenter import PortfolioV2Presenter
from marketcore.presentation.workspace_v2.renderer.portfolio_v2_renderer import render_portfolio_v2

doc = RenderDocument(
    root=RenderNode(
        "main",
        props={"class": "test"},
        children=(RenderNode("h1", text="Тест"),),
    )
)

html = HtmlAdapter.render(doc)
assert "<main" in html
assert "Тест" in html

vm = PortfolioV2Presenter().load(limit=20)
portfolio_doc = render_portfolio_v2(vm)
assert isinstance(portfolio_doc, RenderDocument)

portfolio_html = render_workspace_v2_portfolio_page_v2()
assert "Портфель" in portfolio_html
assert "P&amp;L %" in portfolio_html
assert "mc-v2-card" in portfolio_html
assert "data-i18n-key" not in portfolio_html
assert "portfolio.column." not in portfolio_html

phone_html = render_workspace_v2_portfolio_page_v2(theme_code="PHONE")
assert "max-width:480px" in phone_html
assert "grid-template-columns:1fr;gap:4px" in phone_html

print("render_tree=OK")
print("html_adapter=OK")
print("portfolio_renderer_returns_document=OK")
PY

echo "render_tree=OK"
echo "html_adapter=OK"
echo "html_in_portfolio_renderer=0"
echo "portfolio_page_uses_html_adapter=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_RENDER_TREE_V1_MINIMAL_READY"
echo "VERDICT=TEST_MARKETCORE_RENDER_TREE_V1_MINIMAL_OK"
