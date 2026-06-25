#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GLOBAL_LINK_REPAIR_VALIDATION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_global_link_repair_validation_v1.py

src/scripts/research/build_global_link_repair_validation_v1.py \
  | tee /tmp/global_link_repair_validation_v1.out

grep -q "GLOBAL_LINK_REPAIR_VALIDATION_V1" /tmp/global_link_repair_validation_v1.out
grep -q "closed_trades=437" /tmp/global_link_repair_validation_v1.out
grep -q "linked=437" /tmp/global_link_repair_validation_v1.out
grep -q "not_linked=0" /tmp/global_link_repair_validation_v1.out
grep -q "repaired_links=236" /tmp/global_link_repair_validation_v1.out
grep -q "coverage=1.0000" /tmp/global_link_repair_validation_v1.out
grep -q "duplicates=0" /tmp/global_link_repair_validation_v1.out
grep -q "VERDICT=GLOBAL_LINK_REPAIR_VALIDATION_OK" /tmp/global_link_repair_validation_v1.out

echo "TEST_GLOBAL_LINK_REPAIR_VALIDATION_V1_OK"
