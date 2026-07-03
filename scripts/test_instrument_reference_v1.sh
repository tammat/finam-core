#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_INSTRUMENT_REFERENCE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore/003_instrument_reference_v1.sql

PYTHONPATH=src python -m py_compile src/scripts/build_instrument_reference_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_instrument_reference_v1.py | tee /tmp/instrument_reference_v1.txt

grep -q "VERDICT=INSTRUMENT_REFERENCE_V1_READY" /tmp/instrument_reference_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore.instrument_reference_v1;")
named=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore.instrument_reference_v1 WHERE display_name <> '';")

test "$rows" -gt 0
test "$named" -gt 0

psql -d finam_core -c "
SELECT symbol, display_name, asset_class, exchange, source
FROM marketcore.instrument_reference_v1
ORDER BY symbol
LIMIT 40;
"

echo "instrument_reference_rows=$rows"
echo "named_rows=$named"
echo "VERDICT=TEST_INSTRUMENT_REFERENCE_V1_OK"
