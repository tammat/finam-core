#!/usr/bin/env bash
set -e

echo TEST_PLZL_PROFIT_CONCENTRATION_V1_START

python3 -m py_compile \
src/scripts/analytics/build_plzl_profit_concentration_v1.py

SYMBOL=PLZL@MISX \
python3 src/scripts/analytics/build_plzl_profit_concentration_v1.py \
>/tmp/plzl_profit_concentration_v1.out

grep "TRADE_CONCENTRATION" /tmp/plzl_profit_concentration_v1.out >/dev/null
grep "DAY_CONCENTRATION" /tmp/plzl_profit_concentration_v1.out >/dev/null
grep "VERDICT" /tmp/plzl_profit_concentration_v1.out >/dev/null

echo TEST_PLZL_PROFIT_CONCENTRATION_V1_OK
