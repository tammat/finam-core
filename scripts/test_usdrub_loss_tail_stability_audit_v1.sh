#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_usdrub_loss_tail_stability_audit_v1.py

python3 src/scripts/research/build_usdrub_loss_tail_stability_audit_v1.py \
  | tee /tmp/usdrub_loss_tail_stability_audit_v1.log

grep -q "USDRUB LOSS TAIL STABILITY AUDIT V1" /tmp/usdrub_loss_tail_stability_audit_v1.log
grep -q "AUDIT_DAY_ROW" /tmp/usdrub_loss_tail_stability_audit_v1.log
grep -q "AUDIT_SUMMARY_ROW" /tmp/usdrub_loss_tail_stability_audit_v1.log
grep -q "stability_ratio=" /tmp/usdrub_loss_tail_stability_audit_v1.log
grep -q "negative_ratio=" /tmp/usdrub_loss_tail_stability_audit_v1.log
grep -q "runtime_allow=0" /tmp/usdrub_loss_tail_stability_audit_v1.log
grep -q "execution_enabled=0" /tmp/usdrub_loss_tail_stability_audit_v1.log
grep -q "USDRUB_LOSS_TAIL_STABILITY_AUDIT_V1_OK" /tmp/usdrub_loss_tail_stability_audit_v1.log

echo TEST_USDRUB_LOSS_TAIL_STABILITY_AUDIT_V1_OK
