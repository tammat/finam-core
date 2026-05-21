#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/runtime/exit_policy_advisor.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from finam_core.pipelines.paper_pipeline import log_exit_policy_advisory

assert callable(log_exit_policy_advisory)

print("TEST_EXIT_POLICY_ADVISORY_COMPILE_OK")
PY
