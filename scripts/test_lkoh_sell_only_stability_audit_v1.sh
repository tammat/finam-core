#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_lkoh_sell_only_stability_audit_v1.py

python3 src/scripts/research/build_lkoh_sell_only_stability_audit_v1.py \
  | tee /tmp/lkoh_sell_only_stability_audit_v1.log

grep -q "LKOH SELL ONLY STABILITY AUDIT V1" /tmp/lkoh_sell_only_stability_audit_v1.log
grep -q "AUDIT_DAY_ROW" /tmp/lkoh_sell_only_stability_audit_v1.log
grep -q "AUDIT_SUMMARY_ROW" /tmp/lkoh_sell_only_stability_audit_v1.log
grep -q "stability_ratio=" /tmp/lkoh_sell_only_stability_audit_v1.log
grep -q "profit_concentration_ratio=" /tmp/lkoh_sell_only_stability_audit_v1.log
grep -q "runtime_allow=0" /tmp/lkoh_sell_only_stability_audit_v1.log
grep -q "execution_enabled=0" /tmp/lkoh_sell_only_stability_audit_v1.log
grep -q "LKOH_SELL_ONLY_STABILITY_AUDIT_V1_OK" /tmp/lkoh_sell_only_stability_audit_v1.log

echo TEST_LKOH_SELL_ONLY_STABILITY_AUDIT_V1_OK
