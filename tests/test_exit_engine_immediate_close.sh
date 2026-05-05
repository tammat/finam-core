#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

if grep -R "raw_intent = exit_intent\|self.raw_intent = exit_intent\|self._raw_intent = exit_intent" \
  src/finam_core/pipelines/paper_pipeline.py >/dev/null; then
  echo "FAIL: ExitEngine still stores exit_intent as raw_intent"
  exit 1
fi

grep -R "PIPE_EXIT_ENGINE_ROUTE" src/finam_core/pipelines/paper_pipeline.py >/dev/null

echo "OK: ExitEngine no longer stores exit intent as raw_intent"
