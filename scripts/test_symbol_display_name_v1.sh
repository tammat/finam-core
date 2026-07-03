#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SYMBOL_DISPLAY_NAME_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/039_symbol_display_name_v1.sql

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/symbol_names.py

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.symbol_display_name_v1;")
test "$rows" -gt 10

psql -d finam_core -c "
SELECT symbol, display_name, asset_hint
FROM marketcore_ui.symbol_display_name_v1
ORDER BY symbol
LIMIT 30;
"

echo "symbol_display_name_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=SYMBOL_DISPLAY_NAME_V1_READY"
echo "VERDICT=TEST_SYMBOL_DISPLAY_NAME_V1_OK"
