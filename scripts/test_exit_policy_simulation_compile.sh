#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/exit_policy_simulator.py \
  src/finam_core/analytics/exit_policy_repository.py \
  scripts/analytics/build_exit_policy_simulation.py

echo "TEST_EXIT_POLICY_SIMULATION_COMPILE_OK"
