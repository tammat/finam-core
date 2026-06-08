#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_br_runtime_daily_scorecard_v1.py

python3 src/scripts/analytics/build_br_runtime_daily_scorecard_v1.py | tee /tmp/br_runtime_daily_scorecard_v1.log

grep -q "BR RUNTIME DAILY SCORECARD V1" /tmp/br_runtime_daily_scorecard_v1.log
grep -q "BR_DAILY_SUMMARY" /tmp/br_runtime_daily_scorecard_v1.log
grep -q "BR_DAILY_DETAIL" /tmp/br_runtime_daily_scorecard_v1.log
grep -q "BR_RUNTIME_DAILY_SCORECARD_V1_OK" /tmp/br_runtime_daily_scorecard_v1.log

echo "TEST_BR_RUNTIME_DAILY_SCORECARD_V1_OK"
