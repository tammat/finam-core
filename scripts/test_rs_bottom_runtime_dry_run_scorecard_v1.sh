#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_RUNTIME_DRY_RUN_SCORECARD_V1 ==="

python3 -m py_compile src/scripts/research/build_rs_bottom_runtime_dry_run_scorecard_v1.py

out="/tmp/rs_bottom_runtime_dry_run_scorecard_v1.log"
python3 src/scripts/research/build_rs_bottom_runtime_dry_run_scorecard_v1.py | tee "$out"

grep -q "RS_BOTTOM_RUNTIME_DRY_RUN_SCORECARD_V1" "$out"
grep -q "SCORECARD_ROWS" "$out"
grep -q "symbol=GDU6@RTSX" "$out"
grep -q "symbol=GLU6@RTSX" "$out"
grep -q "symbol=NGM6@RTSX" "$out"
grep -q "max_drawdown=" "$out"
grep -q "paper_orders=0" "$out"
grep -q "VERDICT=RS_BOTTOM_RUNTIME_DRY_RUN_SCORECARD_CONFIRMED" "$out"

echo "TEST_RS_BOTTOM_RUNTIME_DRY_RUN_SCORECARD_V1_OK"
