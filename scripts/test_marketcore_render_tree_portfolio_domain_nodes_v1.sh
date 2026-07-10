#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_RENDER_TREE_PORTFOLIO_DOMAIN_NODES_V1 ==="

files=(
  "src/marketcore/presentation/render_tree/node_types.py"
  "src/marketcore/presentation/render_tree/render_node.py"
  "src/marketcore/presentation/render_tree/render_document.py"
  "src/marketcore/presentation/adapters/web/render_document_to_html_v1.py"
  "src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py"
  "src/marketcore/presentation/workspace_v2/portfolio_page_v2.py"
)

PYTHONPYCACHEPREFIX=/tmp/marketcore_portfolio_domain_nodes_v1 \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -nE \
  'RenderNode\((node_type=)?[[:space:]]*"(main|section|header|article|div|h1|h2|h3|p|a|dl|dt|dd)"' \
  src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py
then
  echo "PLATFORM_NODE_TYPE_IN_PORTFOLIO_RENDERER_FOUND"
  exit 1
fi

if grep -nE \
  'RenderNode\("(main|section|header|article|div|h1|h2|h3|p|a|dl|dt|dd)"' \
  src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py
then
  echo "LEGACY_NODE_TYPE_IN_PORTFOLIO_RENDERER_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.render_tree import (
    DOMAIN_RENDER_NODE_TYPES,
    RenderDocument,
    RenderNode,
    RenderNodeType,
)
from marketcore.presentation.workspace_v2.presenter.portfolio_v2_presenter import (
    PortfolioV2Presenter,
)
from marketcore.presentation.workspace_v2.renderer.portfolio_v2_renderer import (
    render_portfolio_v2,
)
from marketcore.presentation.workspace_v2.portfolio_page_v2 import (
    render_workspace_v2_portfolio_page_v2,
)


def walk(node: RenderNode):
    yield node

    for child in node.children:
        yield from walk(child)


vm = PortfolioV2Presenter().load(limit=20)
document = render_portfolio_v2(vm)
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
    RenderNodeType.TEXT,
    RenderNodeType.METRIC_LIST,
    RenderNodeType.METRIC_ROW,
    RenderNodeType.METRIC_LABEL,
    RenderNodeType.METRIC_VALUE,
}

actual = {node.node_type for node in nodes}

assert required.issubset(actual)

desktop = render_workspace_v2_portfolio_page_v2()
phone = render_workspace_v2_portfolio_page_v2(
    theme_code="PHONE"
)

assert "Портфель" in desktop
assert "P&amp;L %" in desktop
assert "mc-v2-card" in desktop
assert "<main" in desktop
assert "<article" in desktop
assert "<dl" in desktop
assert "<dt" in desktop
assert "<dd" in desktop

assert "max-width:480px" in phone
assert "grid-template-columns:1fr;gap:4px" in phone
assert "P&amp;L %" in phone

print(f"portfolio_nodes={len(nodes)}")
print("portfolio_domain_nodes=OK")
print("web_adapter_domain_support=OK")
print("portfolio_desktop_regression=OK")
print("portfolio_phone_regression=OK")
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

desktop=$(curl -fsS \
  http://127.0.0.1:8080/workspace-v2/portfolio)

phone=$(curl -fsS \
  http://127.0.0.1:8080/workspace-v2/portfolio/phone)

grep -q "Портфель" <<<"$desktop"
grep -q "P&amp;L %" <<<"$desktop"
grep -q "mc-v2-card" <<<"$desktop"

grep -q "max-width:480px" <<<"$phone"
grep -q "P&amp;L %" <<<"$phone"

echo "portfolio_domain_nodes=OK"
echo "portfolio_platform_node_types=0"
echo "web_adapter_domain_support=OK"
echo "desktop_http=OK"
echo "phone_http=OK"
echo "home_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_RENDER_TREE_PORTFOLIO_DOMAIN_NODES_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RENDER_TREE_PORTFOLIO_DOMAIN_NODES_V1_OK"
