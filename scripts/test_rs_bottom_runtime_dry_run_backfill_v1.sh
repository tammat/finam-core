#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_RUNTIME_DRY_RUN_BACKFILL_V1 ==="

python3 -m py_compile src/scripts/research/build_rs_bottom_runtime_dry_run_backfill_v1.py

out="/tmp/rs_bottom_runtime_dry_run_backfill_v1.log"
python3 src/scripts/research/build_rs_bottom_runtime_dry_run_backfill_v1.py | tee "$out"

grep -q "target_table=analytics_rs_bottom_runtime_dry_run_v1" "$out"
grep -q "symbol=GDU6@RTSX" "$out"
grep -q "symbol=GLU6@RTSX" "$out"
grep -q "symbol=NGM6@RTSX" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "real_trading_enabled=0" "$out"
grep -q "paper_orders=0" "$out"
grep -q "VERDICT=RS_BOTTOM_RUNTIME_DRY_RUN_BACKFILL_OK" "$out"

echo "TEST_RS_BOTTOM_RUNTIME_DRY_RUN_BACKFILL_V1_OK"
