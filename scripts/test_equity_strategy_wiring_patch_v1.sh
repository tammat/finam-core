#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY STRATEGY WIRING PATCH V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py
python3 -m py_compile src/scripts/runtime/build_equity_strategy_wiring_patch_v1_dry_run.py

grep -q "EQUITY_STRATEGY_WIRING_PATCH_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "def _runtime_strategy_name_for_symbol" src/finam_core/pipelines/paper_pipeline.py
grep -q "runtime_active_universe" src/finam_core/pipelines/paper_pipeline.py
grep -q "StrategyFactory.create(" src/finam_core/pipelines/paper_pipeline.py
grep -q "strategy_name=strategy_name" src/finam_core/pipelines/paper_pipeline.py

EQUITY_WIRING_DRY_RUN_SYMBOL="${EQUITY_WIRING_DRY_RUN_SYMBOL:-SBER@MISX}" \
PYTHONPATH=src python3 src/scripts/runtime/build_equity_strategy_wiring_patch_v1_dry_run.py \
  | tee /tmp/equity_strategy_wiring_patch_v1.log

grep -q "EQUITY_STRATEGY_WIRING_PATCH_V1_DRY_RUN_OK" /tmp/equity_strategy_wiring_patch_v1.log
grep -q "resolved_strategy=VOLATILITY_BREAKOUT_EQUITY" /tmp/equity_strategy_wiring_patch_v1.log
grep -q "strategy_instance_class=VolatilityBreakoutEquity" /tmp/equity_strategy_wiring_patch_v1.log
grep -q "resolved_to_volatility=1" /tmp/equity_strategy_wiring_patch_v1.log
grep -q "runtime_changes_required=0" /tmp/equity_strategy_wiring_patch_v1.log
grep -q "execution_changes_required=0" /tmp/equity_strategy_wiring_patch_v1.log
grep -q "db_update=0" /tmp/equity_strategy_wiring_patch_v1.log
grep -q "file_update=0" /tmp/equity_strategy_wiring_patch_v1.log
grep -q "VERDICT=EQUITY_STRATEGY_WIRING_PATCH_DRY_RUN_READY" /tmp/equity_strategy_wiring_patch_v1.log

echo
echo "=== EQUITY STRATEGY WIRING PATCH V1 SUMMARY ==="
grep -E "resolved_strategy=|factory_call_variant=|strategy_instance_class=|resolved_to_volatility=|VERDICT=" \
  /tmp/equity_strategy_wiring_patch_v1.log

echo TEST_EQUITY_STRATEGY_WIRING_PATCH_V1_OK
