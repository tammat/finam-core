#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_br_short_entry_enablement_research_v1.py

python3 src/scripts/analytics/build_br_short_entry_enablement_research_v1.py | \
  tee /tmp/br_short_entry_enablement_research_v1.log

grep -q "BR SHORT ENTRY ENABLEMENT RESEARCH V1" /tmp/br_short_entry_enablement_research_v1.log
grep -q "SIGNAL_LAYER" /tmp/br_short_entry_enablement_research_v1.log
grep -q "EXECUTION_INTENT_LAYER" /tmp/br_short_entry_enablement_research_v1.log
grep -q "TRADE_POSITION_LAYER" /tmp/br_short_entry_enablement_research_v1.log
grep -Eq "VERDICT=BR_OPEN_SHORT_ALREADY_ENABLED|VERDICT=BR_OPEN_SHORT_NOT_ENABLED" \
  /tmp/br_short_entry_enablement_research_v1.log

echo BR_SHORT_ENTRY_ENABLEMENT_RESEARCH_V1_OK
