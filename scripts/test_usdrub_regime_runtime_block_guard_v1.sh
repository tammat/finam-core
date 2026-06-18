#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST USDRUB REGIME RUNTIME BLOCK GUARD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "def _is_runtime_strategy_blocked_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "USDRUB_REGIME_RUNTIME_BLOCK_GUARD_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_RUNTIME_STRATEGY_BLOCKED_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "runtime_strategy_selection" src/finam_core/pipelines/paper_pipeline.py
grep -q "USDRUBF@RTSX" src/finam_core/pipelines/paper_pipeline.py
grep -q "USDRUB_REGIME" src/finam_core/pipelines/paper_pipeline.py

echo TEST_USDRUB_REGIME_RUNTIME_BLOCK_GUARD_V1_OK
