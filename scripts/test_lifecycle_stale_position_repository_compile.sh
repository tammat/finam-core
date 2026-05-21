#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/portfolio/lifecycle_stale_position_advisor.py \
  src/finam_core/portfolio/lifecycle_stale_position_repository.py \
  src/scripts/build_lifecycle_stale_position_advice.py

echo "TEST_LIFECYCLE_STALE_POSITION_REPOSITORY_COMPILE_OK"
