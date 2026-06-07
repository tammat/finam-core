#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_ng_time_exit_replacement_candidates_v1.py

python3 src/scripts/analytics/build_ng_time_exit_replacement_candidates_v1.py | \
  tee /tmp/ng_time_exit_replacement_candidates_v1.log

grep -q "NG TIME EXIT REPLACEMENT CANDIDATES V1" /tmp/ng_time_exit_replacement_candidates_v1.log
grep -q "CANDIDATE_RESULTS" /tmp/ng_time_exit_replacement_candidates_v1.log
grep -q "current_time_exit" /tmp/ng_time_exit_replacement_candidates_v1.log
grep -q "hold_bucket_extend_under_60m" /tmp/ng_time_exit_replacement_candidates_v1.log
grep -q "break_even_proxy" /tmp/ng_time_exit_replacement_candidates_v1.log
grep -q "NG_TIME_EXIT_REPLACEMENT_CANDIDATES_V1_OK" /tmp/ng_time_exit_replacement_candidates_v1.log

echo TEST_NG_TIME_EXIT_REPLACEMENT_CANDIDATES_V1_OK
