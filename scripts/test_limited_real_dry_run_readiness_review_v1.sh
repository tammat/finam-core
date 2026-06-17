#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST LIMITED REAL DRY RUN READINESS REVIEW V1 ==="

python3 -m py_compile src/scripts/research/build_limited_real_dry_run_readiness_review_v1.py
python3 -m py_compile src/scripts/research/build_clean_operational_position_view_v1.py
python3 -m py_compile src/scripts/research/build_clean_operational_position_metrics_view_v1.py
python3 -m py_compile src/scripts/research/build_runtime_operational_governance_alignment_v1.py

echo
echo "=== 1. REBUILD OPERATIONAL VIEWS ==="
python3 src/scripts/research/build_clean_operational_position_view_v1.py \
  | tee /tmp/dry_run_readiness_operational_view_v1.log

python3 src/scripts/research/build_clean_operational_position_metrics_view_v1.py \
  | tee /tmp/dry_run_readiness_operational_metrics_v1.log

grep -q "CLEAN_OPERATIONAL_POSITION_VIEW_V1_OK" /tmp/dry_run_readiness_operational_view_v1.log
grep -q "CLEAN_OPERATIONAL_POSITION_METRICS_VIEW_V1_OK" /tmp/dry_run_readiness_operational_metrics_v1.log

echo
echo "=== 2. RUNTIME ALIGNMENT CHECK ==="
python3 src/scripts/research/build_runtime_operational_governance_alignment_v1.py \
  | tee /tmp/dry_run_readiness_runtime_alignment_v1.log

grep -q "RUNTIME_OPERATIONAL_GOVERNANCE_ALIGNMENT_V1_OK" /tmp/dry_run_readiness_runtime_alignment_v1.log
grep -q "BLOCKERS=none" /tmp/dry_run_readiness_runtime_alignment_v1.log

echo
echo "=== 3. LIMITED REAL DRY RUN READINESS REVIEW ==="
python3 src/scripts/research/build_limited_real_dry_run_readiness_review_v1.py \
  | tee /tmp/limited_real_dry_run_readiness_review_v1.log

grep -q "LIMITED_REAL_DRY_RUN_READINESS_REVIEW_V1_OK" /tmp/limited_real_dry_run_readiness_review_v1.log
grep -q "research_ready=1" /tmp/limited_real_dry_run_readiness_review_v1.log
grep -q "paper_ready=1" /tmp/limited_real_dry_run_readiness_review_v1.log
grep -q "shadow_ready=1" /tmp/limited_real_dry_run_readiness_review_v1.log
grep -q "limited_real_dry_run_review_ready=0" /tmp/limited_real_dry_run_readiness_review_v1.log
grep -q "real_execution_ready=0" /tmp/limited_real_dry_run_readiness_review_v1.log
grep -q "production_trading_ready=0" /tmp/limited_real_dry_run_readiness_review_v1.log
grep -q "runtime_allow=0" /tmp/limited_real_dry_run_readiness_review_v1.log
grep -q "execution_enabled=0" /tmp/limited_real_dry_run_readiness_review_v1.log
grep -q "FUTURES_REAL_TRADING_BLOCKED_UNTIL_2026_07_01" /tmp/limited_real_dry_run_readiness_review_v1.log

echo TEST_LIMITED_REAL_DRY_RUN_READINESS_REVIEW_V1_OK
