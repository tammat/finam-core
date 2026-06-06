#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/br_long_governance_v1.py \
  src/scripts/analytics/build_br_long_governance_report_v1.py

BR_LONG_MODE=shadow python3 src/scripts/analytics/build_br_long_governance_report_v1.py | \
  tee /tmp/br_long_governance_v1_shadow.log

grep -q "BR LONG GOVERNANCE REPORT V1" /tmp/br_long_governance_v1_shadow.log
grep -q "BR_LONG_MODE=shadow" /tmp/br_long_governance_v1_shadow.log
grep -q "VERDICT=BR_LONG_SHADOW" /tmp/br_long_governance_v1_shadow.log
grep -q "symbol=BRN6@RTSX side=BUY mode=shadow allowed=0 shadow_logged=1" \
  /tmp/br_long_governance_v1_shadow.log

BR_LONG_MODE=disabled python3 src/scripts/analytics/build_br_long_governance_report_v1.py | \
  tee /tmp/br_long_governance_v1_disabled.log

grep -q "BR_LONG_MODE=disabled" /tmp/br_long_governance_v1_disabled.log
grep -q "VERDICT=BR_LONG_DISABLED" /tmp/br_long_governance_v1_disabled.log
grep -q "symbol=BRN6@RTSX side=BUY mode=disabled allowed=0 shadow_logged=0" \
  /tmp/br_long_governance_v1_disabled.log

echo BR_LONG_GOVERNANCE_V1_OK
