#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/futures_context_normalizer.py \
  src/scripts/build_futures_context_snapshots.py

grep -q "futures_context_snapshots" src/finam_core/research/futures_context_normalizer.py
grep -q "days_to_expiration" src/finam_core/research/futures_context_normalizer.py
grep -q "FUTURES_CONTEXT_SNAPSHOTS_REBUILT" src/scripts/build_futures_context_snapshots.py

echo "TEST_FUTURES_CONTEXT_NORMALIZER_OK"
