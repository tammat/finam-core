#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/runtime/build_runtime_capital_allocator.py

grep -q "market_radar_strategy_mapping" src/scripts/runtime/build_runtime_capital_allocator.py
grep -q "COALESCE(m.strategy" src/scripts/runtime/build_runtime_capital_allocator.py

echo "TEST_MARKET_RADAR_STRATEGY_MAPPING_ALLOCATOR_OK"
