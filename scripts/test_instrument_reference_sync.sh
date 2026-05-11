#!/usr/bin/env bash
set -euo pipefail

test -f sql/20260510_instrument_reference.sql

test -f src/finam_core/instruments/finam_instrument_sync.py

test -x scripts/sync_instruments_from_finam.sh

grep -q "instrument_reference" \
  sql/20260510_instrument_reference.sql

grep -q "FINAM_SECURITIES_URL" \
  src/finam_core/instruments/finam_instrument_sync.py

grep -q "ON CONFLICT(symbol)" \
  src/finam_core/instruments/finam_instrument_sync.py

echo "INSTRUMENT_REFERENCE_SYNC_OK"
