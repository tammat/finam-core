#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export PYTHON_BIN="${PYTHON_BIN:-/opt/finam-core/.venv/bin/python}"

"${PYTHON_BIN}" \
  -m finam_core.instruments.finam_instrument_sync
