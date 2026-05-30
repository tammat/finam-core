#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_NG_HISTORICAL_REPLAY_RESEARCH_V1_START"

python -m py_compile src/scripts/analytics/build_ng_historical_replay_research_v1.py

python src/scripts/analytics/build_ng_historical_replay_research_v1.py \
  > /tmp/ng_historical_replay_research_v1.out

grep -q "NG_HISTORICAL_REPLAY_RESEARCH_V1" /tmp/ng_historical_replay_research_v1.out
grep -q "NG_RESEARCH_SUMMARY" /tmp/ng_historical_replay_research_v1.out
grep -q "NG_RESEARCH_BARS" /tmp/ng_historical_replay_research_v1.out
grep -q "NG_RESEARCH_RETURNS" /tmp/ng_historical_replay_research_v1.out
grep -q "NG_RESEARCH_BREAKOUT_SIGNALS" /tmp/ng_historical_replay_research_v1.out
grep -q "NG_HISTORICAL_REPLAY_RESEARCH_V1_OK" /tmp/ng_historical_replay_research_v1.out

echo "TEST_NG_HISTORICAL_REPLAY_RESEARCH_V1_OK"
