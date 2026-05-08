#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

set -a
. /opt/finam-core/.env.paper_safe
set +a

export PYTHONPATH=src
export REAL_TRADING_ENABLED=0
export EXECUTION_ENABLED=0
export MODE=SIM
export APP_PROFILE=SIM

echo "ORCHESTRATOR_SAFE_ENV mode=${MODE} execution=${EXECUTION_ENABLED} real=${REAL_TRADING_ENABLED}"

exec /opt/finam-core/venv/bin/python -m scripts.run_orchestrator
