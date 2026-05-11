#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

if [ -f /opt/finam-core/.env ]; then
  set -a
  source /opt/finam-core/.env
  set +a
fi

export PYTHONPATH=src
export PYTHON_BIN="${PYTHON_BIN:-/opt/finam-core/.venv/bin/python}"

"${PYTHON_BIN}" -m finam_core.portfolio.finam_real_portfolio_sync
