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

exec env PYTHONPATH=src PAPER_SAFETY_MONITOR_INTERVAL_SEC="${PAPER_SAFETY_MONITOR_INTERVAL_SEC:-60}" \
  venv/bin/python -u src/scripts/run_paper_safety_monitor_v1.py
