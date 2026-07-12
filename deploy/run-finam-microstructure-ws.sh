#!/bin/bash
set -euo pipefail
cd /opt/finam-core
set -a
source .env
set +a
exec env PYTHONPATH=/opt/finam-core/src PYTHONDONTWRITEBYTECODE=1 \
  /opt/finam-core/.venv/bin/python -u src/scripts/run_finam_microstructure_ws_v1.py
