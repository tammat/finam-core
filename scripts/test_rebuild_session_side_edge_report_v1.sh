#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

export PYTHONPATH=src

echo "TEST_REBUILD_SESSION_SIDE_EDGE_REPORT_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_rebuild_session_side_edge_report_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "REBUILD_SESSION_SIDE_EDGE_REPORT_V1" "$TMP_LOG"
grep -q "REBUILD_SESSION_SIDE_EDGE_STATUS" "$TMP_LOG"
grep -q "REBUILD_SESSION_SIDE_EDGE_ROW" "$TMP_LOG"
grep -q "REBUILD_SESSION_SIDE_EDGE_REPORT_V1_OK" "$TMP_LOG"

echo "TEST_REBUILD_SESSION_SIDE_EDGE_REPORT_V1_OK"
