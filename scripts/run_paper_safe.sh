#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

set -a
source .env.paper_safe
set +a

exec env PYTHONPATH=src venv/bin/python -u src/scripts/run_market_pipeline.py \
  --symbol BRM6@RTSX \
  --symbols BRM6@RTSX,SBER@MISX,PLZL@MISX \
  --strategy vwap_bands_mr \
  --run-secs 0 \
  --quote-log-every 30 \
  --enable-filter-engine
