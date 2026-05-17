#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/runtime_subprocess_worker.py \
  src/finam_core/runtime/runtime_execution_engine.py

python - <<'PY'
from finam_core.runtime.runtime_subprocess_worker import RuntimeSubprocessWorker

worker = RuntimeSubprocessWorker("SBER@MISX", run_secs=1)

assert worker.symbol == "SBER@MISX"
assert worker.run_secs == 1
assert worker.process is None

print("OK: RuntimeSubprocessWorker compile")
PY
