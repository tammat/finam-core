#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

set -a
source .env.paper_safe
source config/runtime/paper_safe_execution_policy_v1.env
set +a

# Активные фьючерсы берём из свежего аудируемого DB-решения. При устаревшем
# решении сервис завершается и systemd повторяет запуск, не включая старый контракт.
BR_CONTRACT="$(PYTHONPATH=src venv/bin/python src/scripts/resolve_runtime_contract_v1.py --root BR)"
NG_CONTRACT="$(PYTHONPATH=src venv/bin/python src/scripts/resolve_runtime_contract_v1.py --root NG)"
USDRUB_CONTRACT="${USDRUB_CONTRACT:-USDRUBF@RTSX}"
REAL_EXECUTION_SYMBOL_ALLOWLIST="${BR_CONTRACT}"
export BR_CONTRACT NG_CONTRACT USDRUB_CONTRACT REAL_EXECUTION_SYMBOL_ALLOWLIST

PORTFOLIO_SYMBOLS="${BR_CONTRACT},${USDRUB_CONTRACT},SBERP@MISX,PLZL@MISX,LKOH@MISX,VTBR@MISX,NVTK@MISX,X5@MISX,SFIN@MISX,OZON@MISX,EUTR@MISX,T@MISX,${NG_CONTRACT}"

exec env PYTHONPATH=src venv/bin/python -u src/scripts/run_market_pipeline.py \
  --symbol "${BR_CONTRACT}" \
  --symbols "${PORTFOLIO_SYMBOLS}" \
  --strategy vwap_bands_mr \
  --run-secs 0 \
  --quote-log-every 30 \
  --enable-filter-engine
