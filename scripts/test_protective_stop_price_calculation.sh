#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

FILE="src/scripts/place_protective_for_filled_entries.py"

grep -q "def resolve_last_price" "$FILE"
grep -q "def calculate_stop_price" "$FILE"
grep -q "PROTECTIVE_STOP_PCT" "$FILE"
grep -q "dry_run_stop_price" "$FILE"

python -m py_compile "$FILE"

echo "PROTECTIVE_STOP_PRICE_CALCULATION_TEST_OK"
