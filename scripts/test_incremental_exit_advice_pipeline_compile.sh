#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/incremental_exit_intelligence.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from finam_core.pipelines.paper_pipeline import log_incremental_exit_advice

assert callable(log_incremental_exit_advice)

print("TEST_INCREMENTAL_EXIT_ADVICE_PIPELINE_COMPILE_OK")
PY
