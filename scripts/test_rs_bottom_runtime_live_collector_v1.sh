#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_V1 ==="

python3 -m py_compile src/scripts/research/run_rs_bottom_runtime_live_collector_v1.py

out="/tmp/rs_bottom_runtime_live_collector_v1.log"
python3 src/scripts/research/run_rs_bottom_runtime_live_collector_v1.py | tee "$out"

grep -q "RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_V1" "$out"
grep -q "mode=shadow_live_collect" "$out"
grep -q "symbol=GDU6@RTSX" "$out"
grep -q "symbol=GLU6@RTSX" "$out"
grep -q "symbol=NGM6@RTSX" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "real_trading_enabled=0" "$out"
grep -q "paper_orders=0" "$out"
grep -q "VERDICT=RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_OK" "$out"

echo "TEST_RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_V1_OK"
