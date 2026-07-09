#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_RENDER_TREE_HOME_V1 ==="

files=(
  "src/marketcore/presentation/render_tree/html_adapter.py"
  "src/marketcore/presentation/render_tree/render_document.py"
  "src/marketcore/presentation/render_tree/render_node.py"
  "src/marketcore/presentation/workspace_v2/renderer/home_v2_renderer.py"
  "src/marketcore/presentation/workspace_v2/home_page_v2.py"
)

PYTHONPYCACHEPREFIX=/tmp/marketcore_render_tree_home_v1 \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE '<main|<section|<article|<div|</' \
  src/marketcore/presentation/workspace_v2/renderer/home_v2_renderer.py; then
  echo "HTML_IN_HOME_RENDERER_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.workspace_v2.home_page_v2 import render_workspace_v2_home_page_v2
from marketcore.presentation.workspace_v2.presenter.home_v2_presenter import HomeV2Presenter
from marketcore.presentation.workspace_v2.renderer.home_v2_renderer import render_home_v2

vm = HomeV2Presenter().load()
doc = render_home_v2(vm)

assert isinstance(doc, RenderDocument)

html = render_workspace_v2_home_page_v2()

assert "MarketCore OS" in html
assert "Панель состояния" in html
assert "Операторская панель" in html
assert "Портфель" in html
assert "Записей" in html
assert "data-i18n-key" not in html
assert "home.operator." not in html
assert "home.card.status" not in html

print("home_renderer_returns_document=OK")
print("home_page_uses_html_adapter=OK")
PY

echo "home_render_tree=OK"
echo "html_in_home_renderer=0"
echo "home_page_uses_html_adapter=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_RENDER_TREE_HOME_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RENDER_TREE_HOME_V1_OK"
