#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY PRE SIGNAL GUARD STRATEGY WIRING PATCH V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py
python3 -m py_compile src/scripts/runtime/build_equity_runtime_trace_after_wiring_patch_v1.py

grep -q "EQUITY_PRE_SIGNAL_GUARD_STRATEGY_WIRING_PATCH_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "def _runtime_strategy_name_for_symbol" src/finam_core/pipelines/paper_pipeline.py
grep -q "_runtime_strategy_name_for_symbol(str(sym))" src/finam_core/pipelines/paper_pipeline.py
grep -q 'block_type="VOL_LOW_BLOCK"' src/finam_core/pipelines/paper_pipeline.py
grep -q 'block_type="COMPRESSION_WATCH"' src/finam_core/pipelines/paper_pipeline.py

echo
echo "=== PATCHED PRE SIGNAL GUARD LINES ==="
grep -n "EQUITY_PRE_SIGNAL_GUARD_STRATEGY_WIRING_PATCH_V1\\|_runtime_strategy_name_for_symbol(str(sym))\\|block_type=\"VOL_LOW_BLOCK\"\\|block_type=\"COMPRESSION_WATCH\"" \
  src/finam_core/pipelines/paper_pipeline.py

echo TEST_EQUITY_PRE_SIGNAL_GUARD_STRATEGY_WIRING_PATCH_V1_OK
