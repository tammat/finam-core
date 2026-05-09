#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export FORCE_ONCE_BUY=1
export PIPE_DEBUG=1
export RISK_SOFT=1
export EXIT_ON_FILL=1
export SESSION_OVERRIDE=1
export SIMULATE_MARKET=1
export RUN_SECS=20
export SESSION_OVERRIDE_LOG_SEC=10

LOG_FILE="/tmp/forced_pipeline_risk_gate_smoke.log"

python -m src.scripts.run_market_pipeline 2>&1 | tee "$LOG_FILE"

grep -q "PIPE_FORCE_SIGNAL" "$LOG_FILE"
grep -q "PIPE_RISK_OK" "$LOG_FILE"
grep -q "PIPE_PORTFOLIO_RISK_OK" "$LOG_FILE"
grep -q "PIPE_FILLED paper .* side=BUY" "$LOG_FILE"
grep -q "PIPE_EXIT_ENGINE_ROUTE" "$LOG_FILE"
grep -q "PIPE_EXIT_HARD_RISK_OK" "$LOG_FILE"
grep -q "PIPE_FILLED paper .* side=SELL" "$LOG_FILE"
grep -q "PIPE_EXIT_ENGINE_SM_FILLED .* qty_after=0.0" "$LOG_FILE"

if grep -q "PIPE_ENTRY_POINT_SELECTED" "$LOG_FILE"; then
  echo "ERROR: exit intent passed through entry point selector"
  exit 1
fi

echo "FORCED_PIPELINE_RISK_GATE_SMOKE_OK"
