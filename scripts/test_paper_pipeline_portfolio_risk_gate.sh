#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/risk/portfolio_risk_gate.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PortfolioRiskGate" src/finam_core/pipelines/paper_pipeline.py
grep -q "gate=portfolio_risk" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_PAPER_PIPELINE_PORTFOLIO_RISK_GATE_OK"
