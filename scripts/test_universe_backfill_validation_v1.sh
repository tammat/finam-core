#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_UNIVERSE_BACKFILL_VALIDATION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_universe_backfill_validation_v1.py

src/scripts/research/build_universe_backfill_validation_v1.py \
  | tee /tmp/universe_backfill_validation_v1.out

grep -q "UNIVERSE_BACKFILL_VALIDATION_V1" /tmp/universe_backfill_validation_v1.out
grep -q "TARGET_VALIDATION" /tmp/universe_backfill_validation_v1.out
grep -q "TARGET name=BRENT" /tmp/universe_backfill_validation_v1.out
grep -q "TARGET name=NATURAL_GAS" /tmp/universe_backfill_validation_v1.out
grep -q "TARGET name=USD_RUB" /tmp/universe_backfill_validation_v1.out
grep -q "TARGET name=SBER" /tmp/universe_backfill_validation_v1.out
grep -q "snapshots_total=" /tmp/universe_backfill_validation_v1.out
grep -q "duplicates=0" /tmp/universe_backfill_validation_v1.out
grep -q "failures=0" /tmp/universe_backfill_validation_v1.out
grep -q "VERDICT=UNIVERSE_BACKFILL_VALIDATION_OK" /tmp/universe_backfill_validation_v1.out

echo "TEST_UNIVERSE_BACKFILL_VALIDATION_V1_OK"
