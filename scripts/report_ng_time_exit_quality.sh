#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 src/scripts/analytics/build_exit_reason_quality_report_v1.py \
  --root NG \
  --source closed_trade_engine_v1_1 \
  --trusted-from "2026-06-03 00:00:00+00" \
  --exit-reason time_exit \
  --group-by hour_msk,hold_bucket,side
