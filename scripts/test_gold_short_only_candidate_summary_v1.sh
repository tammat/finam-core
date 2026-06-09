#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
src/scripts/research/build_gold_short_only_candidate_summary_v1.py

python3 \
src/scripts/research/build_gold_short_only_candidate_summary_v1.py \
| tee /tmp/gold_short_only_candidate_summary_v1.log

grep -q "GOLD SHORT ONLY CANDIDATE SUMMARY V1" \
/tmp/gold_short_only_candidate_summary_v1.log

grep -q "PROFILE_ROW" \
/tmp/gold_short_only_candidate_summary_v1.log

grep -q "FINAL_VERDICT" \
/tmp/gold_short_only_candidate_summary_v1.log

grep -q "GOLD_SHORT_ONLY_CANDIDATE_SUMMARY_V1_OK" \
/tmp/gold_short_only_candidate_summary_v1.log

echo TEST_GOLD_SHORT_ONLY_CANDIDATE_SUMMARY_V1_OK
