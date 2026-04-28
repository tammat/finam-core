#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -f ".env" ]; then
  set -a
  source ".env"
  set +a
fi

source .venv/bin/activate
export PYTHONPATH=src

python -u src/scripts/run_market_pipeline.py \
  --symbol "${SYMBOL:-BRM6@RTSX}" \
  --symbols "${SYMBOLS:-${SYMBOL:-BRM6@RTSX}}" \
  --strategy "${PIPELINE_STRATEGY:-vwap_bands_mr}" \
  --run-secs "${RUN_SECS:-0}" \
  --quote-log-every "${QUOTE_LOG_EVERY:-30}" \
  --enable-filter-engine
