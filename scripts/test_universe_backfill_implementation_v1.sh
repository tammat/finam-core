#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_UNIVERSE_BACKFILL_IMPLEMENTATION_V1 ==="

python3 -m py_compile src/scripts/research/build_universe_backfill_implementation_v1.py

PYTHONPATH=src timeout 60 \
src/scripts/research/build_universe_backfill_implementation_v1.py --limit 50 \
| tee /tmp/universe_backfill_implementation_v1.out

grep -q "VERDICT=UNIVERSE_BACKFILL_IMPLEMENTATION_OK" /tmp/universe_backfill_implementation_v1.out
grep -q "runtime_changed=0" /tmp/universe_backfill_implementation_v1.out
grep -q "execution_changed=0" /tmp/universe_backfill_implementation_v1.out
grep -q "real_trading_enabled=0" /tmp/universe_backfill_implementation_v1.out
grep -q "orders_sent=0" /tmp/universe_backfill_implementation_v1.out

echo "TEST_UNIVERSE_BACKFILL_IMPLEMENTATION_V1_OK"
