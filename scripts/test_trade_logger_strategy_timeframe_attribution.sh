#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/storage/postgres.py

grep -q 'payload.get("strategy")' src/finam_core/storage/postgres.py
grep -q 'payload.get("timeframe")' src/finam_core/storage/postgres.py
grep -q 'nested_payload.get("strategy")' src/finam_core/storage/postgres.py
grep -q 'nested_payload.get("timeframe")' src/finam_core/storage/postgres.py
grep -q 'RETURNING id' src/finam_core/storage/postgres.py

echo "TRADE_LOGGER_STRATEGY_TIMEFRAME_ATTRIBUTION_OK"
