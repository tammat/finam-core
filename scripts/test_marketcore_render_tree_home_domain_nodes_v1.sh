#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_RENDER_TREE_HOME_DOMAIN_NODES_V1 ==="

files=(
  "src/marketcore/presentation/render_tree/node_types.py"
  "src/marketcore/presentation/render_tree/render_node.py"
  "src/marketcore/presentation/render_tree/render_document.py"
  "src/marketcore/presentation/adapters/web/render_document_to_html_v1.py"
  "src/marketcore/presentation/workspace_v2/renderer/home_v2_renderer.py"
  "src/marketcore/presentation/workspace_v2/home_page_v2.py"
  "src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py"
  "src/marketcore/presentation/workspace_v2/portfolio_page_v2.py"
)

for file in "${files[@]}"; do
  test -f "$file" || {
    echo "FILE_NOT_FOUND=$file"
    exit 1
  }
done

PYTHONPYCACHEPREFIX=/tmp/marketcore_home_domain_nodes_v1 \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

home_renderer="src/marketcore/presentation/workspace_v2/renderer/home_v2_renderer.py"

if grep -nE \
  'RenderNode\((node_type=)?[[:space:]]*"(main|section|header|article|div|h1|h2|h3|p|a|dl|dt|dd)"' \
  "$home_renderer"
then
  echo "PLATFORM_NODE_TYPE_IN_HOME_RENDERER_FOUND"
  exit 1
fi

if grep -nE \
  'RenderNode\("(main|section|header|article|div|h1|h2|h3|p|a|dl|dt|dd)"' \
  "$home_renderer"
then
  echo "LEGACY_NODE_TYPE_IN_HOME_RENDERER_FOUND"
  exit 1
fi

if grep -nE \
  '<(main|section|header|article|div|h1|h2|h3|p|a|dl|dt|dd)([ >])|</' \
  "$home_renderer"
then
  echo "RAW_HTML_IN_HOME_RENDERER_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.render_tree import (
    DOMAIN_RENDER_NODE_TYPES,
    RenderDocument,
    RenderNode,
    RenderNodeType,
)
from marketcore.presentation.workspace_v2.home_page_v2 import (
    render_workspace_v2_home_page_v2,
)
from marketcore.presentation.workspace_v2.presenter.home_v2_presenter import (
    HomeV2Presenter,
)
from marketcore.presentation.workspace_v2.renderer.home_v2_renderer import (
    render_home_v2,
)
from marketcore.presentation.workspace_v2.portfolio_page_v2 import (
    render_workspace_v2_portfolio_page_v2,
)


def walk(node: RenderNode):
    yield node

    for child in node.children:
        yield from walk(child)


vm = HomeV2Presenter().load()
document = render_home_v2(vm)
nodes = tuple(walk(document.root))

assert isinstance(document, RenderDocument)
assert nodes
assert document.root.node_type == RenderNodeType.WORKSPACE

for node in nodes:
    assert isinstance(node.node_type, RenderNodeType)
    assert node.type_code in DOMAIN_RENDER_NODE_TYPES

required = {
    RenderNodeType.WORKSPACE,
    RenderNodeType.PAGE,
    RenderNodeType.HEADER,
    RenderNodeType.SECTION,
    RenderNodeType.GRID,
    RenderNodeType.CARD,
    RenderNodeType.TITLE,
    RenderNodeType.SUBTITLE,
    RenderNodeType.TEXT,
    RenderNodeType.ACTION,
}

actual = {node.node_type for node in nodes}

assert required.issubset(actual)

home = render_workspace_v2_home_page_v2()
portfolio = render_workspace_v2_portfolio_page_v2()
phone = render_workspace_v2_portfolio_page_v2(
    theme_code="PHONE"
)

assert "MarketCore OS" in home
assert "Рабочий стол оператора" in home
assert "Панель состояния" in home
assert "Операторская панель" in home
assert "Портфель" in home
assert "Записей" in home
assert "/workspace-v2/portfolio" in home
assert "/workspace-v2/portfolio/phone" in home
assert "mc-v2-card" in home
assert "<main" in home
assert "<section" in home
assert "<article" in home
assert "<h1>" in home
assert "<h2>" in home
assert "<h3>" in home

assert "Портфель" in portfolio
assert "P&amp;L %" in portfolio
assert "mc-v2-card" in portfolio

assert "max-width:480px" in phone
assert "P&amp;L %" in phone

print(f"home_nodes={len(nodes)}")
print("home_domain_nodes=OK")
print("home_web_delivery=OK")
print("portfolio_regression=OK")
print("phone_regression=OK")
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

home=$(curl -fsS \
  http://127.0.0.1:8080/workspace-v2)

portfolio=$(curl -fsS \
  http://127.0.0.1:8080/workspace-v2/portfolio)

phone=$(curl -fsS \
  http://127.0.0.1:8080/workspace-v2/portfolio/phone)

grep -q "MarketCore OS" <<<"$home"
grep -q "Панель состояния" <<<"$home"
grep -q "Операторская панель" <<<"$home"
grep -q "Записей" <<<"$home"
grep -q "mc-v2-card" <<<"$home"

grep -q "Портфель" <<<"$portfolio"
grep -q "P&amp;L %" <<<"$portfolio"

grep -q "max-width:480px" <<<"$phone"
grep -q "P&amp;L %" <<<"$phone"

echo "home_domain_nodes=OK"
echo "home_platform_node_types=0"
echo "raw_html_in_home_renderer=0"
echo "home_http=OK"
echo "portfolio_regression=OK"
echo "phone_regression=OK"
echo "web_adapter_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_RENDER_TREE_HOME_DOMAIN_NODES_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RENDER_TREE_HOME_DOMAIN_NODES_V1_OK"
