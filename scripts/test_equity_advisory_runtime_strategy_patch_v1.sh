#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_ADVISORY_RUNTIME_STRATEGY_PATCH_V1 ==="

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "EQUITY_ADVISORY_RUNTIME_STRATEGY_PATCH_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "_runtime_strategy_name_for_symbol(str(sym))" src/finam_core/pipelines/paper_pipeline.py
grep -q "_runtime_strategy_name_for_symbol(symbol)" src/finam_core/pipelines/paper_pipeline.py

echo "VERDICT=EQUITY_ADVISORY_RUNTIME_STRATEGY_PATCH_OK"
echo "TEST_EQUITY_ADVISORY_RUNTIME_STRATEGY_PATCH_V1_OK"
