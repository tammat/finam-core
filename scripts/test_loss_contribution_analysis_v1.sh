#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_loss_contribution_analysis_v1.py

python3 src/scripts/research/build_loss_contribution_analysis_v1.py | \
  tee /tmp/loss_contribution_analysis_v1.log

grep -q "LOSS CONTRIBUTION ANALYSIS V1" /tmp/loss_contribution_analysis_v1.log
grep -q "SUMMARY" /tmp/loss_contribution_analysis_v1.log
grep -q "LOSS_BY_SYMBOL" /tmp/loss_contribution_analysis_v1.log
grep -q "PARETO_LOSS_CONCENTRATION" /tmp/loss_contribution_analysis_v1.log
grep -Eq "VERDICT=OK|VERDICT=INSUFFICIENT_DATA" /tmp/loss_contribution_analysis_v1.log

echo LOSS_CONTRIBUTION_ANALYSIS_V1_OK
