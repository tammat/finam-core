#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/portfolio/portfolio_heat_engine.py \
  src/finam_core/portfolio/portfolio_heat_repository.py \
  src/scripts/build_portfolio_heat.py

echo "TEST_PORTFOLIO_HEAT_REPOSITORY_COMPILE_OK"
