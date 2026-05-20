#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/execution/duplicate_fill_protection.py

grep -q "duplicate_filled_order" src/finam_core/execution/duplicate_fill_protection.py
grep -q "broker_order_id" src/finam_core/execution/duplicate_fill_protection.py

echo "OK: duplicate fill protection"
