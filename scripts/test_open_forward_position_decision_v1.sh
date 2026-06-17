#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST OPEN FORWARD POSITION DECISION V1 ==="

python3 -m py_compile src/scripts/research/build_open_forward_position_decision_v1.py

python3 src/scripts/research/build_open_forward_position_decision_v1.py \
  | tee /tmp/open_forward_position_decision_v1.log

grep -q "OPEN_FORWARD_POSITION_DECISION_V1_OK" /tmp/open_forward_position_decision_v1.log
grep -q "VERDICT=OPEN_FORWARD_POSITION_DECISIONS_READY" /tmp/open_forward_position_decision_v1.log
grep -q "runtime_allow=0" /tmp/open_forward_position_decision_v1.log
grep -q "execution_enabled=0" /tmp/open_forward_position_decision_v1.log

grep -q "symbol=BRM6@RTSX .*decision=EXCLUDE_FROM_CURRENT_FORWARD_OPEN_STATE" /tmp/open_forward_position_decision_v1.log
grep -q "symbol=BRN6@RTSX .*decision=KEEP_AS_OPEN_PAPER_LONG_TAIL" /tmp/open_forward_position_decision_v1.log
grep -q "symbol=USDRUBF@RTSX .*decision=QUARANTINE_FROM_CLEAN_FORWARD_STATE" /tmp/open_forward_position_decision_v1.log

echo TEST_OPEN_FORWARD_POSITION_DECISION_V1_OK
