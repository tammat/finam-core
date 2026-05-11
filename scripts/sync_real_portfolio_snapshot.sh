#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export PYTHON_BIN="${PYTHON_BIN:-/opt/finam-core/.venv/bin/python}"

if [ -z "${REAL_PORTFOLIO_JSON:-}" ]; then
  echo "REAL_PORTFOLIO_JSON is required"
  exit 1
fi

"${PYTHON_BIN}" -m finam_core.portfolio.real_portfolio_snapshot
