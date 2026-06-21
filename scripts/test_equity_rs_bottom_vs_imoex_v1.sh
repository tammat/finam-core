#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_RS_BOTTOM_VS_IMOEX_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_equity_rs_bottom_vs_imoex_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_equity_rs_bottom_vs_imoex_v1.py | tee "$out"

grep -q "TEST_EQUITY_RS_BOTTOM_VS_IMOEX_V1_OK" "$out"
grep -q "db_update=0" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"
grep -Eq "VERDICT=EQUITY_RS_BOTTOM_VS_IMOEX_(READY|NO_DATA)" "$out"

if grep -q "VERDICT=EQUITY_RS_BOTTOM_VS_IMOEX_READY" "$out"; then
  grep -q "EQUITY_RS_VS_IMOEX_ROW" "$out"
fi

echo "VERDICT=EQUITY_RS_BOTTOM_VS_IMOEX_TEST_OK"
echo "TEST_EQUITY_RS_BOTTOM_VS_IMOEX_V1_OK"
