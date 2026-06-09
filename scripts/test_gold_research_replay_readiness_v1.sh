#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_gold_research_replay_readiness_v1.py

python3 src/scripts/analytics/build_gold_research_replay_readiness_v1.py \
  | tee /tmp/gold_research_replay_readiness_v1.log

grep -q "GOLD RESEARCH REPLAY READINESS V1" \
    /tmp/gold_research_replay_readiness_v1.log

grep -q "REPLAY_ROWS" \
    /tmp/gold_research_replay_readiness_v1.log

grep -q "GDM6@RTSX" \
    /tmp/gold_research_replay_readiness_v1.log

grep -q "GOLD_RESEARCH_REPLAY_READINESS_V1_OK" \
    /tmp/gold_research_replay_readiness_v1.log

echo "TEST_GOLD_RESEARCH_REPLAY_READINESS_V1_OK"
