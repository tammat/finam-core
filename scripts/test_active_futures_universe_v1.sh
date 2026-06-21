#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_ACTIVE_FUTURES_UNIVERSE_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_active_futures_universe_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_active_futures_universe_v1.py | tee "$out"

grep -q "VERDICT=ACTIVE_FUTURES_UNIVERSE_READY" "$out"
grep -q "TEST_ACTIVE_FUTURES_UNIVERSE_V1_OK" "$out"
grep -q '"db_update": 0' "$out"
grep -q '"runtime_changed": 0' "$out"
grep -q '"execution_changed": 0' "$out"
grep -q '"telegram_send": 0' "$out"
grep -q "ACTIVE_FUTURES_ROW" "$out"
grep -q "USDRUBF@RTSX" "$out"

if grep -E "ACTIVE_FUTURES_ROW symbol=.*quality=EXCLUDE" "$out"; then
  echo "ERROR: excluded contract leaked into active universe"
  exit 1
fi

if grep -E "ACTIVE_FUTURES_ROW symbol=(BRJ6|BRK6|BRV5|NGF6|NGG6|NGH6)" "$out"; then
  echo "ERROR: stale contract leaked into active universe"
  exit 1
fi

echo "VERDICT=ACTIVE_FUTURES_UNIVERSE_TEST_OK"
echo "TEST_ACTIVE_FUTURES_UNIVERSE_V1_OK"
