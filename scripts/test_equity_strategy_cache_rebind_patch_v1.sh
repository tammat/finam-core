#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_STRATEGY_CACHE_REBIND_PATCH_V1 ==="

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "EQUITY_STRATEGY_CACHE_REBIND_PATCH_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_EQUITY_STRATEGY_CACHE_REBOUND" src/finam_core/pipelines/paper_pipeline.py
grep -q "StrategyFactory.create" src/finam_core/pipelines/paper_pipeline.py

echo "VERDICT=EQUITY_STRATEGY_CACHE_REBIND_PATCH_OK"
echo "TEST_EQUITY_STRATEGY_CACHE_REBIND_PATCH_V1_OK"
