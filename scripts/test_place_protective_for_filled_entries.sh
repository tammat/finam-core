#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f src/scripts/place_protective_for_filled_entries.py

grep -q "PROTECTIVE_PLACEMENT_CHECK" src/scripts/place_protective_for_filled_entries.py
grep -q "AUTO_REAL_PROTECTIVE_ORDERS" src/scripts/place_protective_for_filled_entries.py

python -m py_compile src/scripts/place_protective_for_filled_entries.py

echo "PLACE_PROTECTIVE_FOR_FILLED_ENTRIES_TEST_OK"
