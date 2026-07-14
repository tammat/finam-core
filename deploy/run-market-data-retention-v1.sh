#!/bin/bash
set -euo pipefail

cd /opt/finam-core
set -a
source .env
set +a

exec env PYTHONPATH=/opt/finam-core/src PYTHONDONTWRITEBYTECODE=1 \
  /opt/finam-core/.venv/bin/python src/scripts/run_market_data_retention_v1.py "$@"
