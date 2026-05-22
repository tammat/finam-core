#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/futures_contract_universe_repository.py \
  src/scripts/seed_futures_contract_universe.py

grep -q "futures_contract_universe" src/finam_core/research/futures_contract_universe_repository.py
grep -q "BRM6@RTSX" src/scripts/seed_futures_contract_universe.py
grep -q "NGM6@RTSX" src/scripts/seed_futures_contract_universe.py
grep -q "USDRUBF@RTSX" src/scripts/seed_futures_contract_universe.py

echo "TEST_FUTURES_CONTRACT_UNIVERSE_OK"
