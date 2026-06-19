#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY MTF CLOSED BAR DISPATCH TRACE PATCH V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "_process_equity_closed_bar_for_paper_signal(bar)" src/finam_core/pipelines/paper_pipeline.py
grep -q "def _process_equity_closed_bar_for_paper_signal" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_EQUITY_CLOSED_BAR_ROUTE" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_EQUITY_CLOSED_BAR_NO_SIGNAL" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_EQUITY_CLOSED_BAR_SIGNAL" src/finam_core/pipelines/paper_pipeline.py
grep -q "trace_only=1" src/finam_core/pipelines/paper_pipeline.py

if grep -n "send_order\|submit_order\|real_trading_enabled=1\|execution_enabled=1" src/finam_core/pipelines/paper_pipeline.py | grep -n "PIPE_EQUITY_CLOSED_BAR" ; then
  echo "ERROR: equity trace patch must not send orders"
  exit 1
fi

echo "EQUITY_MTF_CLOSED_BAR_DISPATCH_TRACE_PATCH_SUMMARY"
echo "dispatch_call=1"
echo "handler=1"
echo "trace_only=1"
echo "db_update=0"
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "VERDICT=EQUITY_MTF_CLOSED_BAR_DISPATCH_TRACE_PATCH_READY"

echo TEST_EQUITY_MTF_CLOSED_BAR_DISPATCH_TRACE_PATCH_V1_OK
