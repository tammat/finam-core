#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_exit_reason_top_clusters_v1.py

python3 src/scripts/analytics/build_exit_reason_top_clusters_v1.py \
  --root NG \
  --source closed_trade_engine_v1_1 \
  --trusted-from "2026-06-03 00:00:00+00" \
  --min-trades 2 \
  --limit 5 | tee /tmp/exit_reason_top_clusters_ng.log

grep -q "EXIT REASON TOP CLUSTERS V1" /tmp/exit_reason_top_clusters_ng.log
grep -q "TOP_CLUSTERS" /tmp/exit_reason_top_clusters_ng.log
grep -q "BOTTOM_CLUSTERS" /tmp/exit_reason_top_clusters_ng.log
grep -q "EXIT_REASON_TOP_CLUSTERS_V1_OK" /tmp/exit_reason_top_clusters_ng.log

python3 src/scripts/analytics/build_exit_reason_top_clusters_v1.py \
  --root BR \
  --source closed_trade_engine_v1_1 \
  --trusted-from "2026-06-05 00:00:00+00" \
  --min-trades 2 \
  --limit 5 | tee /tmp/exit_reason_top_clusters_br.log

grep -q "EXIT_REASON_TOP_CLUSTERS_V1_OK" /tmp/exit_reason_top_clusters_br.log

echo TEST_EXIT_REASON_TOP_CLUSTERS_V1_OK
