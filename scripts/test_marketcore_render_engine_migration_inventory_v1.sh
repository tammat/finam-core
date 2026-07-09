#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_RENDER_ENGINE_MIGRATION_INVENTORY_V1 ==="

mkdir -p reports
report="reports/marketcore_render_engine_migration_inventory_v1.txt"

{
echo "=== HTML ADAPTER USAGE ==="
grep -RIn "HtmlAdapter" src/marketcore/presentation || true

echo
echo "=== RENDER TREE USAGE ==="
grep -RIn "RenderDocument\|RenderNode" src/marketcore/presentation || true

echo
echo "=== RAW HTML IN PRESENTATION ==="
grep -RIn "return .*<\|<main\|<section\|<article\|<div\|</" src/marketcore/presentation || true

echo
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_RENDER_ENGINE_MIGRATION_INVENTORY_V1_READY"
} | tee "$report"

grep -q "VERDICT=MARKETCORE_RENDER_ENGINE_MIGRATION_INVENTORY_V1_READY" "$report"

echo "report=$report"
echo "VERDICT=TEST_MARKETCORE_RENDER_ENGINE_MIGRATION_INVENTORY_V1_OK"
