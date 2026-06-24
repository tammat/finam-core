#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_EVENING_SESSION_FILTER_APPLY_DRY_RUN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_evening_session_filter_apply_dry_run_v1.py

src/scripts/research/build_evening_session_filter_apply_dry_run_v1.py \
  | tee /tmp/evening_session_filter_apply_dry_run_v1.out

grep -q "EVENING_SESSION_FILTER_APPLY_DRY_RUN_V1" /tmp/evening_session_filter_apply_dry_run_v1.out
grep -q "DRY_RUN_ROW symbol=GDU6@RTSX planned_decision=ALLOW_RESEARCH_SHADOW" /tmp/evening_session_filter_apply_dry_run_v1.out
grep -q "DRY_RUN_ROW symbol=GDU6@RTSX planned_decision=BLOCK_EVENING_SESSION" /tmp/evening_session_filter_apply_dry_run_v1.out
grep -q "DRY_RUN_ROW symbol=GLU6@RTSX planned_decision=ALLOW_RESEARCH_SHADOW" /tmp/evening_session_filter_apply_dry_run_v1.out
grep -q "DRY_RUN_ROW symbol=GLU6@RTSX planned_decision=BLOCK_EVENING_SESSION" /tmp/evening_session_filter_apply_dry_run_v1.out
grep -q "runtime_changed=0" /tmp/evening_session_filter_apply_dry_run_v1.out
grep -q "real_trading_enabled=0" /tmp/evening_session_filter_apply_dry_run_v1.out
grep -q "VERDICT=EVENING_SESSION_FILTER_APPLY_DRY_RUN_READY" /tmp/evening_session_filter_apply_dry_run_v1.out

echo "TEST_EVENING_SESSION_FILTER_APPLY_DRY_RUN_V1_OK"
