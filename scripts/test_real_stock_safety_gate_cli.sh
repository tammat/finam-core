#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

export PYTHONPATH=src
export REAL_STOCKS_ONLY=1

set +e
EXECUTION_MODE=real python -u src/scripts/run_market_pipeline.py \
  --symbol BRM6@RTSX --symbols BRM6@RTSX >/tmp/real_futures_gate.log 2>&1
FUTURES_RC=$?
set -e

test "$FUTURES_RC" -eq 3
grep -q "REAL_STOCK_SAFETY_GATE_BLOCK" /tmp/real_futures_gate.log
grep -q "REAL_STOCK_GATE_BLOCKED_FUTURES" /tmp/real_futures_gate.log

set +e
timeout 10s env EXECUTION_MODE=real python -u src/scripts/run_market_pipeline.py \
  --symbol SBER@MISX --symbols SBER@MISX >/tmp/real_stock_gate.log 2>&1
STOCK_RC=$?
set -e

grep -q "REAL_STOCK_SAFETY_GATE_OK" /tmp/real_stock_gate.log

echo "REAL_STOCK_SAFETY_GATE_CLI_TEST_OK"
