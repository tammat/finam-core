#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY PRE SIGNAL GUARD RUNTIME VALUE PROBE V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "EQUITY_PRE_SIGNAL_GUARD_RUNTIME_VALUE_PROBE_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_EQUITY_PRE_SIGNAL_GUARD_STRATEGY_RESOLVED" src/finam_core/pipelines/paper_pipeline.py
grep -q "_pre_signal_guard_strategy" src/finam_core/pipelines/paper_pipeline.py
grep -q 'block_type="VOL_LOW_BLOCK"' src/finam_core/pipelines/paper_pipeline.py
grep -q 'block_type="COMPRESSION_WATCH"' src/finam_core/pipelines/paper_pipeline.py
grep -q "strategy=_pre_signal_guard_strategy" src/finam_core/pipelines/paper_pipeline.py

echo
echo "=== PROBE LINES ==="
grep -n "EQUITY_PRE_SIGNAL_GUARD_RUNTIME_VALUE_PROBE_V1\\|PIPE_EQUITY_PRE_SIGNAL_GUARD_STRATEGY_RESOLVED\\|_pre_signal_guard_strategy\\|block_type=\"VOL_LOW_BLOCK\"\\|block_type=\"COMPRESSION_WATCH\"" \
  src/finam_core/pipelines/paper_pipeline.py

echo TEST_EQUITY_PRE_SIGNAL_GUARD_RUNTIME_VALUE_PROBE_V1_OK
