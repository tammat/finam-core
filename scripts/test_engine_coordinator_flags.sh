#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/engine/coordinator_flags.py \
  src/finam_core/engine/restart_recovery_coordinator.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
import os

from finam_core.engine.coordinator_flags import CoordinatorFlags

for key in (
    "ENABLE_ENGINE_COORDINATOR",
    "ENABLE_ENGINE_COORDINATOR_ON_QUOTE",
    "ENABLE_ENGINE_COORDINATOR_RECONCILE",
    "ENABLE_ENGINE_COORDINATOR_EXECUTION_ROUTE",
):
    os.environ.pop(key, None)

assert CoordinatorFlags.enabled() is False
assert CoordinatorFlags.on_quote_enabled() is False
assert CoordinatorFlags.reconcile_enabled() is False
assert CoordinatorFlags.execution_route_enabled() is False

os.environ["ENABLE_ENGINE_COORDINATOR"] = "1"

assert CoordinatorFlags.enabled() is True
assert CoordinatorFlags.on_quote_enabled() is True
assert CoordinatorFlags.reconcile_enabled() is True
assert CoordinatorFlags.execution_route_enabled() is True

print("OK: engine coordinator flags")
PY

python - <<'PY'
from pathlib import Path

paper = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")
recovery = Path("src/finam_core/engine/restart_recovery_coordinator.py").read_text(encoding="utf-8")

assert "from finam_core.engine.coordinator_flags import CoordinatorFlags" in paper
assert "CoordinatorFlags.on_quote_enabled()" in paper
assert "CoordinatorFlags.execution_route_enabled()" in paper

assert "from finam_core.engine.coordinator_flags import CoordinatorFlags" in recovery
assert "CoordinatorFlags.reconcile_enabled()" in recovery

print("OK: CoordinatorFlags usage after RestartRecoveryCoordinator extraction")
PY
