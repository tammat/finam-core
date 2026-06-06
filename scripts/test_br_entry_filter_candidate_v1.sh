#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_br_entry_filter_candidate_v1.py

python3 src/scripts/analytics/build_br_entry_filter_candidate_v1.py | \
  tee /tmp/br_entry_filter_candidate_v1.log

grep -q "BR ENTRY FILTER CANDIDATE V1" /tmp/br_entry_filter_candidate_v1.log
grep -q "FILTER_CANDIDATES" /tmp/br_entry_filter_candidate_v1.log
grep -q "ACCEPTED_FILTERS" /tmp/br_entry_filter_candidate_v1.log
grep -q "RECOMMENDATION" /tmp/br_entry_filter_candidate_v1.log
grep -Eq "VERDICT=FILTER_CANDIDATE_FOUND|VERDICT=NO_FILTER_CANDIDATE|VERDICT=NO_DATA" \
  /tmp/br_entry_filter_candidate_v1.log

echo BR_ENTRY_FILTER_CANDIDATE_V1_OK
