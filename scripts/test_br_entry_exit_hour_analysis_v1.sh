#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_br_entry_exit_hour_analysis_v1.py

python3 src/scripts/analytics/build_br_entry_exit_hour_analysis_v1.py \
  | tee /tmp/br_entry_exit_hour_analysis_v1.log

grep -q "BR ENTRY EXIT HOUR ANALYSIS V1" \
  /tmp/br_entry_exit_hour_analysis_v1.log

grep -q "VERDICT=" \
  /tmp/br_entry_exit_hour_analysis_v1.log

echo TEST_BR_ENTRY_EXIT_HOUR_ANALYSIS_V1_OK
