#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/futures_contract_universe_repository.py \
  src/scripts/resolve_futures_active_contracts.py

grep -q "resolve_active_contract" src/finam_core/research/futures_contract_universe_repository.py
grep -q "resolve_research_contracts" src/finam_core/research/futures_contract_universe_repository.py
grep -q "status <> 'QUARANTINE'" src/finam_core/research/futures_contract_universe_repository.py
grep -q "FUTURES_ACTIVE_CONTRACT" src/scripts/resolve_futures_active_contracts.py
grep -q "FUTURES_RESEARCH_CONTRACTS" src/scripts/resolve_futures_active_contracts.py

echo "TEST_FUTURES_ACTIVE_CONTRACT_RESOLVER_OK"
