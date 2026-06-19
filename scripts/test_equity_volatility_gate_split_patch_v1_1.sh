#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY VOLATILITY GATE SPLIT PATCH V1.1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "EQUITY_ATR_MIN_PCT" src/finam_core/pipelines/paper_pipeline.py
grep -q "equity_volatility_too_low" src/finam_core/pipelines/paper_pipeline.py
grep -q "ATR_MIN_PCT" src/finam_core/pipelines/paper_pipeline.py
grep -q "br_volatility_too_low" src/finam_core/pipelines/paper_pipeline.py

echo
echo "=== PATCHED CONTEXT ==="
grep -n -A8 -B4 "EQUITY_ATR_MIN_PCT" src/finam_core/pipelines/paper_pipeline.py
grep -n -A8 -B4 "equity_volatility_too_low" src/finam_core/pipelines/paper_pipeline.py

echo TEST_EQUITY_VOLATILITY_GATE_SPLIT_PATCH_V1_1_OK
