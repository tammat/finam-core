#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/portfolio/portfolio_intelligence_snapshot.py \
  src/finam_core/portfolio/portfolio_intelligence_repository.py \
  src/scripts/build_portfolio_intelligence_snapshot.py

echo "TEST_BUILD_PORTFOLIO_INTELLIGENCE_SNAPSHOT_COMPILE_OK"
