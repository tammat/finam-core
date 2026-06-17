#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== NG M1 MULTI SYMBOL ROUTING V1 ==="
echo "mode=static_audit"
echo "runtime_allow=0"
echo "execution_enabled=0"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "def _ng_m1_runtime_symbols_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "def _ng_m1_breakout_for_symbol_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "ng_m1_breakout_by_symbol" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_NG_M1_STRATEGY_INIT" src/finam_core/pipelines/paper_pipeline.py

if grep -q "bar.symbol != self.ng_m1_breakout_symbol" src/finam_core/pipelines/paper_pipeline.py; then
  echo "FAIL: old single-symbol NG M1 guard still exists"
  exit 1
fi

if grep -q "self.ng_m1_breakout.on_signal_bar" src/finam_core/pipelines/paper_pipeline.py; then
  echo "FAIL: old single-instance NG M1 strategy call still exists"
  exit 1
fi

echo "NG_M1_MULTI_SYMBOL_ROUTING_V1_OK"
