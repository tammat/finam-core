#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_portfolio_execution_queue.py \
  src/finam_core/runtime/portfolio_execution_planner.py

grep -q "portfolio_execution_queue" src/scripts/run_portfolio_execution_queue.py
grep -q "PORTFOLIO_EXECUTION_QUEUE_OK" src/scripts/run_portfolio_execution_queue.py
grep -q "queue_state" sql/20260519_portfolio_execution_queue.sql

echo "OK: portfolio execution queue"
