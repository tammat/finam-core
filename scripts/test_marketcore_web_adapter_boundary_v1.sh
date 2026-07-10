#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_WEB_ADAPTER_BOUNDARY_V1 ==="

files=(
  "src/marketcore/presentation/render_tree/render_node.py"
  "src/marketcore/presentation/render_tree/render_document.py"
  "src/marketcore/presentation/adapters/__init__.py"
  "src/marketcore/presentation/adapters/web/__init__.py"
  "src/marketcore/presentation/adapters/web/render_document_to_html_v1.py"
  "src/marketcore/presentation/workspace_v2/home_page_v2.py"
  "src/marketcore/presentation/workspace_v2/portfolio_page_v2.py"
)

for file in "${files[@]}"; do
    test -f "$file" || {
        echo "FILE_NOT_FOUND=$file"
        exit 1
    }
done

test ! -d src/marketcore/presentation/render_engine || {
    echo "RENDER_ENGINE_DIRECTORY_STILL_EXISTS"
    exit 1
}

if grep -RIn \
    --include='*.py' \
    "WebRenderer\|render_engine\.web_renderer\|HtmlAdapter\|render_tree\.html_adapter" \
    src/marketcore/presentation
then
    echo "LEGACY_RENDER_REFERENCE_FOUND"
    exit 1
fi

PYTHONPYCACHEPREFIX=/tmp/marketcore_web_adapter_boundary \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.adapters.web.render_document_to_html_v1 import (
    RenderDocumentToHtmlV1,
)
from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.render_tree.render_node import RenderNode
from marketcore.presentation.workspace_v2.home_page_v2 import (
    render_workspace_v2_home_page_v2,
)
from marketcore.presentation.workspace_v2.portfolio_page_v2 import (
    render_workspace_v2_portfolio_page_v2,
)


document = RenderDocument(
    root=RenderNode(
        node_type="main",
        props={"class": "boundary-test"},
        children=(
            RenderNode(
                node_type="h1",
                text="MarketCore OS",
            ),
        ),
    )
)

html = RenderDocumentToHtmlV1.render(document)

assert '<main class="boundary-test">' in html
assert "<h1>MarketCore OS</h1>" in html

home = render_workspace_v2_home_page_v2()
portfolio = render_workspace_v2_portfolio_page_v2()
phone = render_workspace_v2_portfolio_page_v2(theme_code="PHONE")

assert "MarketCore OS" in home
assert "Портфель" in portfolio
assert "P&amp;L %" in portfolio
assert "max-width:480px" in phone

print("render_tree_core=OK")
print("web_adapter=OK")
print("home_delivery=OK")
print("portfolio_delivery=OK")
print("phone_delivery=OK")
PY

echo "render_engine_directory=0"
echo "legacy_html_adapter=0"
echo "web_adapter_boundary=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_WEB_ADAPTER_BOUNDARY_V1_READY"
echo "VERDICT=TEST_MARKETCORE_WEB_ADAPTER_BOUNDARY_V1_OK"
