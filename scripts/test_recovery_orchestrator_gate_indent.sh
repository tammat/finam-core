#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

grep -q "PIPE_RECOVERY_ORCHESTRATOR_BLOCK" src/scripts/run_market_pipeline.py
grep -q "PIPE_RECOVERY_ORCHESTRATOR_OK" src/scripts/run_market_pipeline.py
grep -q "raise SystemExit(2)" src/scripts/run_market_pipeline.py

python -m py_compile src/scripts/run_market_pipeline.py

echo "RECOVERY_ORCHESTRATOR_GATE_INDENT_TEST_OK"
