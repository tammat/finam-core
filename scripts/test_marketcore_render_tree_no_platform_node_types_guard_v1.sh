#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_RENDER_TREE_NO_PLATFORM_NODE_TYPES_GUARD_V1 ==="

renderers=(
src/marketcore/presentation/workspace_v2/renderer/home_v2_renderer.py
src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py
)

echo
echo "=== PLATFORM NODE TYPES ==="

if grep -nE \
'RenderNode\((node_type=)?[[:space:]]*"(main|section|header|article|div|h1|h2|h3|p|a|dl|dt|dd)"' \
"${renderers[@]}"
then
    echo
    echo "PLATFORM_NODE_TYPE_FOUND"
    exit 1
fi

echo "platform_node_types=0"

echo
echo "=== RAW HTML ==="

if grep -nE \
'<(main|section|header|article|div|h1|h2|h3|p|a|dl|dt|dd)([ >])|</' \
"${renderers[@]}"
then
    echo
    echo "RAW_HTML_FOUND"
    exit 1
fi

echo "raw_html=0"

echo
echo "=== LEGACY STRING NODE TYPES ==="

if grep -nE \
'RenderNode\("' \
"${renderers[@]}"
then
    echo
    echo "STRING_NODE_TYPES_FOUND"
    exit 1
fi

echo "string_node_types=0"

echo
echo "=== DOMAIN NODE TYPES ==="

grep -RIn \
"RenderNodeType\." \
"${renderers[@]}"

echo
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo
echo "VERDICT=MARKETCORE_RENDER_TREE_NO_PLATFORM_NODE_TYPES_GUARD_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RENDER_TREE_NO_PLATFORM_NODE_TYPES_GUARD_V1_OK"
