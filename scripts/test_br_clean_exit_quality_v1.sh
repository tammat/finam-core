#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_br_clean_exit_quality_v1.py

python3 src/scripts/analytics/build_br_clean_exit_quality_v1.py | \
  tee /tmp/br_clean_exit_quality_v1.log

grep -q "BR CLEAN EXIT QUALITY V1" /tmp/br_clean_exit_quality_v1.log
grep -q "SUMMARY" /tmp/br_clean_exit_quality_v1.log
grep -q "EXIT_SIMULATION" /tmp/br_clean_exit_quality_v1.log
grep -q "VERDICT=OK" /tmp/br_clean_exit_quality_v1.log

echo BR_CLEAN_EXIT_QUALITY_V1_OK
