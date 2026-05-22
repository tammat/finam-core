#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/exit_alpha_grid.py \
  src/scripts/run_exit_alpha_parameter_grid.py

python - <<'PY'
from finam_core.research.exit_alpha_grid import build_exit_alpha_parameter_grid_v1
grid = build_exit_alpha_parameter_grid_v1()
assert len(grid) == 81
assert len({x.policy_name for x in grid}) == 81
print("TEST_EXIT_ALPHA_PARAMETER_GRID_OK")
PY
