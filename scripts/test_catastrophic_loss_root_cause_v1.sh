#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_catastrophic_loss_root_cause_v1.py

python3 src/scripts/research/build_catastrophic_loss_root_cause_v1.py | \
  tee /tmp/catastrophic_loss_root_cause_v1.log

grep -q "CATASTROPHIC LOSS ROOT CAUSE V1" /tmp/catastrophic_loss_root_cause_v1.log
grep -q "ROOT_CAUSE_COUNTERS" /tmp/catastrophic_loss_root_cause_v1.log
grep -q "DIAGNOSIS" /tmp/catastrophic_loss_root_cause_v1.log
grep -Eq "VERDICT=OK|VERDICT=NO_TARGET_LOSSES" /tmp/catastrophic_loss_root_cause_v1.log

echo CATASTROPHIC_LOSS_ROOT_CAUSE_V1_OK
