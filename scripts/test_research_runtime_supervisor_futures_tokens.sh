#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/scripts/run_research_runtime_supervisor.py \
  src/finam_core/research/futures_contract_universe_repository.py

grep -q "expand_symbol_tokens" src/scripts/run_research_runtime_supervisor.py
grep -q "_ACTIVE" src/scripts/run_research_runtime_supervisor.py
grep -q "_RESEARCH" src/scripts/run_research_runtime_supervisor.py
grep -q "resolve_active_contract" src/scripts/run_research_runtime_supervisor.py
grep -q "resolve_research_contracts" src/scripts/run_research_runtime_supervisor.py

echo "TEST_RESEARCH_RUNTIME_SUPERVISOR_FUTURES_TOKENS_OK"
