#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_RUNTIME_DRY_RUN_PLAN_V1 ==="

python3 -m py_compile src/scripts/research/build_rs_bottom_runtime_dry_run_plan_v1.py

out="/tmp/rs_bottom_runtime_dry_run_plan_v1.log"
python3 src/scripts/research/build_rs_bottom_runtime_dry_run_plan_v1.py | tee "$out"

grep -q "RS_BOTTOM_RUNTIME_DRY_RUN_V1_PLAN" "$out"
grep -q "DRY_RUN_PLAN_ROWS" "$out"
grep -q "target_table=analytics_rs_bottom_runtime_dry_run_v1" "$out"
grep -q "orders_created=0" "$out"
grep -q "VERDICT=RS_BOTTOM_RUNTIME_DRY_RUN_PLAN_READY" "$out"

echo "TEST_RS_BOTTOM_RUNTIME_DRY_RUN_PLAN_V1_OK"
