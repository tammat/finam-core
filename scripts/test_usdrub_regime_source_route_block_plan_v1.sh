#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST USDRUB REGIME SOURCE ROUTE BLOCK PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_usdrub_regime_source_route_block_plan_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_usdrub_regime_source_route_block_plan_v1.py \
  | tee /tmp/usdrub_regime_source_route_block_plan_v1.log

grep -q "USDRUB_REGIME_SOURCE_ROUTE_BLOCK_PLAN_V1_OK" /tmp/usdrub_regime_source_route_block_plan_v1.log
grep -q "USDRUB_SOURCE_ROUTE_BLOCK_PLAN_SUMMARY" /tmp/usdrub_regime_source_route_block_plan_v1.log
grep -q "recommended_primary_patch=paper_pipeline_usdrub_fee_drag_block" /tmp/usdrub_regime_source_route_block_plan_v1.log
grep -q "recommended_disable_env=ENABLE_USDRUBF_PAPER_ACCUMULATION_BYPASS_V1=0" /tmp/usdrub_regime_source_route_block_plan_v1.log
grep -q "db_update=0" /tmp/usdrub_regime_source_route_block_plan_v1.log
grep -q "VERDICT=" /tmp/usdrub_regime_source_route_block_plan_v1.log

echo
echo "=== USDRUB REGIME SOURCE ROUTE BLOCK PLAN SUMMARY ==="
grep -E "USDRUB_BLOCK_PLAN_ENV_ROW|USDRUB_BLOCK_PLAN_TRADE_ROW|runtime_active_match=|runtime_selection_match=|symbol_strategy_map_hit=|paper_bypass_hit=|recommended_|VERDICT=" \
  /tmp/usdrub_regime_source_route_block_plan_v1.log | head -160

echo TEST_USDRUB_REGIME_SOURCE_ROUTE_BLOCK_PLAN_V1_OK
