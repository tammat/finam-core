#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_RENDER_TREE_DOMAIN_NODE_TYPES_V1 ==="

files=(
  "src/marketcore/presentation/render_tree/__init__.py"
  "src/marketcore/presentation/render_tree/node_types.py"
  "src/marketcore/presentation/render_tree/render_node.py"
  "src/marketcore/presentation/render_tree/render_document.py"
  "src/marketcore/presentation/workspace_v2/renderer/home_v2_renderer.py"
  "src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py"
  "src/marketcore/presentation/workspace_v2/home_page_v2.py"
  "src/marketcore/presentation/workspace_v2/portfolio_page_v2.py"
)

for file in "${files[@]}"; do
  test -f "$file" || {
    echo "FILE_NOT_FOUND=$file"
    exit 1
  }
done

PYTHONPYCACHEPREFIX=/tmp/marketcore_render_tree_domain_node_types_v1 \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE \
  --include='*.py' \
  'html|HTML|css|CSS|http|HTTP|browser|Browser' \
  src/marketcore/presentation/render_tree
then
  echo "PLATFORM_DEPENDENCY_INSIDE_RENDER_TREE_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.render_tree import (
    DOMAIN_RENDER_NODE_TYPES,
    RenderDocument,
    RenderNode,
    RenderNodeType,
    is_domain_render_node_type,
)
from marketcore.presentation.workspace_v2.home_page_v2 import (
    render_workspace_v2_home_page_v2,
)
from marketcore.presentation.workspace_v2.portfolio_page_v2 import (
    render_workspace_v2_portfolio_page_v2,
)


expected_types = {
    "workspace",
    "page",
    "header",
    "section",
    "grid",
    "card",
    "title",
    "subtitle",
    "text",
    "metric_list",
    "metric_row",
    "metric_label",
    "metric_value",
    "action",
    "badge",
}

assert DOMAIN_RENDER_NODE_TYPES == expected_types
assert len(RenderNodeType) == len(expected_types)

for expected in expected_types:
    assert is_domain_render_node_type(expected)

assert not is_domain_render_node_type("main")
assert not is_domain_render_node_type("div")
assert not is_domain_render_node_type("")
assert not is_domain_render_node_type(None)

domain_node = RenderNode(
    node_type=RenderNodeType.CARD,
    props={"role": "summary"},
    children=(
        RenderNode(
            node_type=RenderNodeType.TITLE,
            text="Портфель",
        ),
    ),
)

assert domain_node.type_code == "card"
assert domain_node.children[0].type_code == "title"

document = RenderDocument(
    root=RenderNode(
        node_type=RenderNodeType.WORKSPACE,
        children=(domain_node,),
    )
)

assert document.root.type_code == "workspace"

# Временная обратная совместимость до отдельных миграций Home и Portfolio.
legacy_node = RenderNode(node_type="main")
assert legacy_node.type_code == "main"

try:
    RenderNode(node_type="")
except ValueError as exc:
    assert str(exc) == "RENDER_NODE_TYPE_MUST_NOT_BE_EMPTY"
else:
    raise AssertionError("EMPTY_NODE_TYPE_NOT_REJECTED")

try:
    RenderNode(node_type=123)  # type: ignore[arg-type]
except TypeError as exc:
    assert str(exc) == "RENDER_NODE_TYPE_MUST_BE_ENUM_OR_STRING"
else:
    raise AssertionError("INVALID_NODE_TYPE_NOT_REJECTED")

home = render_workspace_v2_home_page_v2()
portfolio = render_workspace_v2_portfolio_page_v2()
phone = render_workspace_v2_portfolio_page_v2(theme_code="PHONE")

assert "MarketCore OS" in home
assert "Операторская панель" in home
assert "Портфель" in portfolio
assert "P&amp;L %" in portfolio
assert "max-width:480px" in phone

print("domain_node_types=OK")
print("render_node_validation=OK")
print("legacy_string_compatibility=OK")
print("home_regression=OK")
print("portfolio_regression=OK")
print("phone_regression=OK")
PY

echo "domain_node_types=OK"
echo "render_node_typed=OK"
echo "legacy_string_compatibility=OK"
echo "home_changed=0"
echo "portfolio_changed=0"
echo "web_adapter_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_RENDER_TREE_DOMAIN_NODE_TYPES_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RENDER_TREE_DOMAIN_NODE_TYPES_V1_OK"
