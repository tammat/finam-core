#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/first_real_order_check.py

grep -q "FIRST_REAL_ORDER_CHECK_OK" src/scripts/first_real_order_check.py
grep -q "FIRST_REAL_ORDER_CHECK_BLOCKED" src/scripts/first_real_order_check.py
grep -q "SBER@MISX" src/scripts/first_real_order_check.py

echo "OK: first real order check"
