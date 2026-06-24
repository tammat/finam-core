#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_SESSION_FILTER_REPLAY_VALIDATION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_session_filter_replay_validation_v1.py

src/scripts/research/build_gold_session_filter_replay_validation_v1.py \
  | tee /tmp/gold_session_filter_replay_validation_v1.out

grep -q "VALIDATION_ROW" \
  /tmp/gold_session_filter_replay_validation_v1.out

grep -q "symbol=GDU6@RTSX" \
  /tmp/gold_session_filter_replay_validation_v1.out

grep -q "symbol=GLU6@RTSX" \
  /tmp/gold_session_filter_replay_validation_v1.out

grep -q "FILTER_BEFORE_19_MSK" \
  /tmp/gold_session_filter_replay_validation_v1.out

grep -q "VERDICT=GOLD_SESSION_FILTER_REPLAY_VALIDATION_READY" \
  /tmp/gold_session_filter_replay_validation_v1.out

echo "TEST_GOLD_SESSION_FILTER_REPLAY_VALIDATION_V1_OK"
