#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_br_clean_loss_breakdown_v1.py

python3 src/scripts/analytics/build_br_clean_loss_breakdown_v1.py | \
  tee /tmp/br_clean_loss_breakdown_v1.log

grep -q "BR CLEAN LOSS BREAKDOWN V1" /tmp/br_clean_loss_breakdown_v1.log
grep -q "scope=clean_non_quarantined_BR" /tmp/br_clean_loss_breakdown_v1.log
grep -q "SUMMARY" /tmp/br_clean_loss_breakdown_v1.log
grep -q "BY_STRATEGY" /tmp/br_clean_loss_breakdown_v1.log
grep -q "TOP_BR_CLEAN_LOSSES" /tmp/br_clean_loss_breakdown_v1.log
grep -q "VERDICT=OK" /tmp/br_clean_loss_breakdown_v1.log

echo BR_CLEAN_LOSS_BREAKDOWN_V1_OK
