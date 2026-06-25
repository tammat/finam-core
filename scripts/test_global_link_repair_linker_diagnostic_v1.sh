#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GLOBAL_LINK_REPAIR_LINKER_DIAGNOSTIC_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_global_link_repair_linker_diagnostic_v1.py

src/scripts/research/build_global_link_repair_linker_diagnostic_v1.py \
  | tee /tmp/global_link_repair_linker_diagnostic_v1.out

grep -q "GLOBAL_LINK_REPAIR_LINKER_DIAGNOSTIC_V1" /tmp/global_link_repair_linker_diagnostic_v1.out
grep -q "TRADE_DIAGNOSTIC_ROWS" /tmp/global_link_repair_linker_diagnostic_v1.out
grep -q "SOURCE_DISTRIBUTION" /tmp/global_link_repair_linker_diagnostic_v1.out
grep -q "DIAGNOSTIC_SUMMARY" /tmp/global_link_repair_linker_diagnostic_v1.out
grep -q "diagnosed_trades=" /tmp/global_link_repair_linker_diagnostic_v1.out
grep -Eq "VERDICT=GLOBAL_LINK_REPAIR_LINKER_DIAGNOSTIC_READY|VERDICT=GLOBAL_LINK_REPAIR_LINKER_DIAGNOSTIC_NO_LOST_TARGET_TRADES" /tmp/global_link_repair_linker_diagnostic_v1.out

echo "TEST_GLOBAL_LINK_REPAIR_LINKER_DIAGNOSTIC_V1_OK"
