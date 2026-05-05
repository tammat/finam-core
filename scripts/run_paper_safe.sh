#!/usr/bin/env bash
# Русский комментарий: активные фьючерсные контракты задаём через переменные,
# чтобы при экспирации переключать контракт без изменения кода сервиса.
BR_CONTRACT="${BR_CONTRACT:-BRM6@RTSX}"
NG_CONTRACT="${NG_CONTRACT:-NGK6@RTSX}"
USDRUB_CONTRACT="${USDRUB_CONTRACT:-USDRUBF@RTSX}"

PORTFOLIO_SYMBOLS="${BR_CONTRACT},${USDRUB_CONTRACT},SBERP@MISX,PLZL@MISX,LKOH@MISX,VTBR@MISX,NVTK@MISX,X5@MISX,SFIN@MISX,OZON@MISX,EUTR@MISX,T@MISX,${NG_CONTRACT}"

set -euo pipefail

cd /opt/finam-core

set -a
source .env.paper_safe
set +a

exec env PYTHONPATH=src venv/bin/python -u src/scripts/run_market_pipeline.py \
  --symbol "${BR_CONTRACT}" \
  --symbols "${PORTFOLIO_SYMBOLS}" \
  --strategy vwap_bands_mr \
  --run-secs 0 \
  --quote-log-every 30 \
  --enable-filter-engine
