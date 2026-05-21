#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/portfolio/portfolio_intelligence_snapshot.py \
  src/finam_core/portfolio/portfolio_intelligence_repository.py

echo "TEST_PORTFOLIO_INTELLIGENCE_REPOSITORY_COMPILE_OK"
