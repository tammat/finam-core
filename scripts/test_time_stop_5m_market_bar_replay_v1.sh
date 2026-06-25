#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_TIME_STOP_5M_MARKET_BAR_REPLAY_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_time_stop_5m_market_bar_replay_v1.py

src/scripts/research/build_time_stop_5m_market_bar_replay_v1.py \
  | tee /tmp/time_stop_5m_market_bar_replay_v1.out

grep -q "TIME_STOP_5M_MARKET_BAR_REPLAY_V1" /tmp/time_stop_5m_market_bar_replay_v1.out
grep -q "SCHEMA_DETECTION" /tmp/time_stop_5m_market_bar_replay_v1.out
grep -q "REPLAY_SCORECARD" /tmp/time_stop_5m_market_bar_replay_v1.out
grep -Eq "VERDICT=TIME_STOP_5M_MARKET_BAR_REPLAY_(READY|SCHEMA_ONLY)" /tmp/time_stop_5m_market_bar_replay_v1.out

echo "TEST_TIME_STOP_5M_MARKET_BAR_REPLAY_V1_OK"
