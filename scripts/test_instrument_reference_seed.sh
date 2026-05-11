#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f src/finam_core/data/instrument_reference_seed.py
test -x scripts/seed_instrument_reference.sh

grep -q "INSTRUMENT_REFERENCE_SEED_OK" src/finam_core/data/instrument_reference_seed.py
grep -q "instrument_reference" src/finam_core/data/instrument_reference_seed.py
grep -q "LKOH@MISX" src/finam_core/data/instrument_reference_seed.py
grep -q "BRM6@RTSX" src/finam_core/data/instrument_reference_seed.py

python -m py_compile src/finam_core/data/instrument_reference_seed.py

echo "INSTRUMENT_REFERENCE_SEED_TEST_OK"
