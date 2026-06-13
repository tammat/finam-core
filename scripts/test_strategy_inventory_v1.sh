#!/usr/bin/env bash
set -euo pipefail
python3 -m py_compile src/scripts/research/build_strategy_inventory_v1.py
python3 src/scripts/research/build_strategy_inventory_v1.py | tee /tmp/strategy_inventory_v1.log
grep -q "STRATEGY_INVENTORY_V1_OK" /tmp/strategy_inventory_v1.log
grep -q "GDU6@RTSX" /tmp/strategy_inventory_v1.log
grep -q "USDRUBF@RTSX" /tmp/strategy_inventory_v1.log
echo TEST_STRATEGY_INVENTORY_V1_OK
