#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BRENT_ROLLOVER_EDGE_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_brent_rollover_edge_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_brent_rollover_edge_v1.py | tee "$out"

grep -q "TEST_BRENT_ROLLOVER_EDGE_V1_OK" "$out"
grep -q "db_update=0" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"
grep -q "rollover_verdict=" "$out"
grep -Eq "VERDICT=BRENT_ROLLOVER_EDGE_(READY|NO_DATA)" "$out"

if grep -q "VERDICT=BRENT_ROLLOVER_EDGE_READY" "$out"; then
  grep -q "BRENT_ROLLOVER_ROW" "$out"
fi

echo "VERDICT=BRENT_ROLLOVER_EDGE_TEST_OK"
echo "TEST_BRENT_ROLLOVER_EDGE_V1_OK"
