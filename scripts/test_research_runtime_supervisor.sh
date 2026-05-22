#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/research_runtime_state_repository.py \
  src/finam_core/research/research_runtime_supervisor.py \
  src/scripts/run_research_runtime_supervisor.py

grep -q "research_runtime_state" src/finam_core/research/research_runtime_state_repository.py
grep -q "research_runtime_cycle_log" src/finam_core/research/research_runtime_state_repository.py
grep -q "RESEARCH_RUNTIME_SUPERVISOR_CYCLE_START" src/finam_core/research/research_runtime_supervisor.py

echo "TEST_RESEARCH_RUNTIME_SUPERVISOR_OK"
