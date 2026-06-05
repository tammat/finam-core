#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_regime_guard_shadow_effectiveness_report_v1.py

python3 src/scripts/research/build_regime_guard_shadow_effectiveness_report_v1.py \
  --since "24 hours" | tee /tmp/regime_guard_shadow_effectiveness_report_v1.log

grep -q "REGIME GUARD SHADOW EFFECTIVENESS REPORT V1" /tmp/regime_guard_shadow_effectiveness_report_v1.log
grep -q "TABLE_EXISTS=" /tmp/regime_guard_shadow_effectiveness_report_v1.log
grep -q "TOTAL_ROWS=" /tmp/regime_guard_shadow_effectiveness_report_v1.log
grep -q "BLOCK_RATE=" /tmp/regime_guard_shadow_effectiveness_report_v1.log
grep -Eq "VERDICT=NO_TABLE|VERDICT=INSUFFICIENT_SHADOW_DATA|VERDICT=READY_FOR_PNL_CORRELATION" \
  /tmp/regime_guard_shadow_effectiveness_report_v1.log

echo REGIME_GUARD_SHADOW_EFFECTIVENESS_REPORT_V1_OK
