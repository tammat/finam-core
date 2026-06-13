#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

test -f src/scripts/analytics/build_time_exit_quality_join_v1.py

python3 -m py_compile src/scripts/analytics/build_time_exit_quality_join_v1.py

python3 src/scripts/analytics/build_time_exit_quality_join_v1.py | \
  tee /tmp/time_exit_quality_join_v1.log

grep -q "TIME EXIT QUALITY JOIN V1" /tmp/time_exit_quality_join_v1.log
grep -q "JOINED_EXIT_QUALITY" /tmp/time_exit_quality_join_v1.log
grep -q "TIME_EXIT_VS_OTHER" /tmp/time_exit_quality_join_v1.log
grep -q "MATCH_COVERAGE" /tmp/time_exit_quality_join_v1.log
grep -q "TIME_EXIT_QUALITY_JOIN_V1_OK" /tmp/time_exit_quality_join_v1.log

echo TEST_TIME_EXIT_QUALITY_JOIN_V1_OK
