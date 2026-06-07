#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 src/scripts/analytics/build_exit_reason_quality_report_v1.py \
  --root BR \
  --source closed_trade_engine_v1_1 \
  --trusted-from "2026-06-05 00:00:00+00" \
  --group-by exit_reason,hour_msk,hold_bucket,side
