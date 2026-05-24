#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.runtime.runtime_strategy_selection_repository import (
    RuntimeStrategySelectionRepository,
)

repo = RuntimeStrategySelectionRepository()
repo.migrate()

print("TEST_RUNTIME_STRATEGY_SELECTION_REPOSITORY_OK")
PY

python -m py_compile \
  src/finam_core/runtime/runtime_strategy_selection_repository.py \
  src/scripts/runtime/build_runtime_strategy_selection.py
