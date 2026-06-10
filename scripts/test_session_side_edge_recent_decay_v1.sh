#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_session_side_edge_recent_decay_v1.py

python3 \
  src/scripts/analytics/build_session_side_edge_recent_decay_v1.py \
  | tee /tmp/session_side_edge_recent_decay_v1.log

grep -q "SESSION SIDE EDGE RECENT DECAY V1" \
  /tmp/session_side_edge_recent_decay_v1.log

grep -q "DECAY_SUMMARY" \
  /tmp/session_side_edge_recent_decay_v1.log

grep -q "VERDICT=" \
  /tmp/session_side_edge_recent_decay_v1.log

grep -q "SESSION_SIDE_EDGE_RECENT_DECAY_V1_OK" \
  /tmp/session_side_edge_recent_decay_v1.log

echo TEST_SESSION_SIDE_EDGE_RECENT_DECAY_V1_OK
