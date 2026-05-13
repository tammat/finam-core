#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

FILE="src/scripts/place_protective_for_filled_entries.py"

grep -q "FinamOrdersClient" "$FILE"
grep -q "place_stop_order" "$FILE"
grep -q "AUTO_REAL_PROTECTIVE_ORDERS" "$FILE"
grep -q "PROTECTIVE_STOP_ORDER_RESULT" "$FILE"
grep -q "protective_side" "$FILE"

python -m py_compile "$FILE"

echo "PROTECTIVE_REAL_STOP_PLACEMENT_PATH_TEST_OK"
