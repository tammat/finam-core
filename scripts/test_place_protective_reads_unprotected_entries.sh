#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

FILE="src/scripts/place_protective_for_filled_entries.py"

grep -q "class UnprotectedEntry" "$FILE"
grep -q "def list_unprotected_entries" "$FILE"
grep -q "protective_order_links" "$FILE"
grep -q "PROTECTIVE_PLACEMENT_CANDIDATE" "$FILE"
grep -q "unprotected_entries=" "$FILE"

python -m py_compile "$FILE"

echo "PLACE_PROTECTIVE_READS_UNPROTECTED_ENTRIES_TEST_OK"
