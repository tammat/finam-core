#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_br_entry_quality_strict_v1.py

python3 src/scripts/analytics/build_br_entry_quality_strict_v1.py | \
  tee /tmp/br_entry_quality_strict_v1.log

grep -q "BR ENTRY QUALITY STRICT V1" /tmp/br_entry_quality_strict_v1.log
grep -q "lookahead_decision=disabled" /tmp/br_entry_quality_strict_v1.log
grep -q "OVERALL" /tmp/br_entry_quality_strict_v1.log
grep -q "BY_STRATEGY" /tmp/br_entry_quality_strict_v1.log
grep -q "BY_ENTRY_HOUR_MSK" /tmp/br_entry_quality_strict_v1.log
grep -q "TOP_BAD_ENTRIES" /tmp/br_entry_quality_strict_v1.log
grep -Eq "VERDICT=OK|VERDICT=NO_DATA" /tmp/br_entry_quality_strict_v1.log

echo BR_ENTRY_QUALITY_STRICT_V1_OK
