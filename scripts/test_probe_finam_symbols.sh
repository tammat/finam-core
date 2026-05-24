#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/ingestion/probe_finam_symbols.py
grep -q "SYMBOL_PROBE_OK" src/scripts/ingestion/probe_finam_symbols.py
grep -q "SYMBOL_PROBE_FAIL" src/scripts/ingestion/probe_finam_symbols.py

echo "TEST_PROBE_FINAM_SYMBOLS_OK"
