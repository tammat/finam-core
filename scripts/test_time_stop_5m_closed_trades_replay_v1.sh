#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_TIME_STOP_5M_CLOSED_TRADES_REPLAY_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_time_stop_5m_closed_trades_replay_v1.py

src/scripts/research/build_time_stop_5m_closed_trades_replay_v1.py \
  | tee /tmp/time_stop_5m_closed_trades_replay_v1.out

grep -q "TIME_STOP_5M_CLOSED_TRADES_REPLAY_V1" /tmp/time_stop_5m_closed_trades_replay_v1.out
grep -q "source_table=closed_trades" /tmp/time_stop_5m_closed_trades_replay_v1.out
grep -q "POLICY name=TIME_STOP_5M" /tmp/time_stop_5m_closed_trades_replay_v1.out
grep -q "EXIT_POLICY_ROW policy=TIME_STOP_5M" /tmp/time_stop_5m_closed_trades_replay_v1.out
grep -q "next_required=TIME_STOP_5M_MARKET_BAR_REPLAY_V1" /tmp/time_stop_5m_closed_trades_replay_v1.out
grep -q "VERDICT=TIME_STOP_5M_CLOSED_TRADES_REPLAY_READY" /tmp/time_stop_5m_closed_trades_replay_v1.out

echo "TEST_TIME_STOP_5M_CLOSED_TRADES_REPLAY_V1_OK"
