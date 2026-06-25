#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GLOBAL_LINK_REPAIR_IMPLEMENTATION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_global_link_repair_implementation_v1.py

src/scripts/research/build_global_link_repair_implementation_v1.py \
  | tee /tmp/global_link_repair_implementation_v1.out

grep -q "GLOBAL_LINK_REPAIR_IMPLEMENTATION_V1" /tmp/global_link_repair_implementation_v1.out
grep -q "repair_type=TIMEFRAME_MISMATCH_MAP_LIVE_M1_TO_M5" /tmp/global_link_repair_implementation_v1.out
grep -q "repaired_rows=" /tmp/global_link_repair_implementation_v1.out
grep -q "still_missing=" /tmp/global_link_repair_implementation_v1.out
grep -q "mapped_timeframes=LIVE->M5,M1->M5" /tmp/global_link_repair_implementation_v1.out
grep -q "db_update=1" /tmp/global_link_repair_implementation_v1.out
grep -q "runtime_changed=0" /tmp/global_link_repair_implementation_v1.out
grep -q "execution_changed=0" /tmp/global_link_repair_implementation_v1.out
grep -q "real_trading_enabled=0" /tmp/global_link_repair_implementation_v1.out
grep -q "orders_sent=0" /tmp/global_link_repair_implementation_v1.out
grep -q "VERDICT=GLOBAL_LINK_REPAIR_IMPLEMENTATION_OK" /tmp/global_link_repair_implementation_v1.out

echo "TEST_GLOBAL_LINK_REPAIR_IMPLEMENTATION_V1_OK"
