#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

set -a
source .env.paper_safe
set +a

exec env PYTHONPATH=src venv/bin/python -u src/scripts/run_market_pipeline.py \
  --symbol BRM6@RTSX \
  --symbols BRM6@RTSX,USDRUBF@RTSX,SBERP@MISX,PLZL@MISX,LKOH@MISX,VTBR@MISX,NVTK@MISX,X5@MISX,SFIN@MISX,OZON@MISX,EUTR@MISX,T@MISX,NGH6@RTSX \
  --strategy vwap_bands_mr \
  --run-secs 0 \
  --quote-log-every 30 \
  --enable-filter-engine
