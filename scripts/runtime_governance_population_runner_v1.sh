#!/usr/bin/env bash
cd /opt/finam-core
set -a
. /opt/finam-core/.env
set +a
echo "RUNTIME_GOV_POP_ENV DATABASE_URL_SET=${DATABASE_URL:+1}"
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/finam-core-pycache}"
mkdir -p "${PYTHONPYCACHEPREFIX}"

SYMBOL="${SYMBOL:-BRM6@RTSX}"
STRATEGY="${STRATEGY:-once_buy}"
RUNS="${RUNS:-5}"
RUN_SECS="${RUN_SECS:-60}"
STARTING_CASH="${STARTING_CASH:-100000}"
WINDOW_HOURS="${WINDOW_HOURS:-168}"

echo "RUNTIME_GOVERNANCE_POPULATION_RUNNER_V1_START"
echo "symbol=${SYMBOL}"
echo "strategy=${STRATEGY}"
echo "runs=${RUNS}"
echo "run_secs=${RUN_SECS}"
echo "starting_cash=${STARTING_CASH}"
echo "window_hours=${WINDOW_HOURS}"

/opt/finam-core/venv/bin/python -m py_compile \
  src/scripts/analytics/build_runtime_governance_population_status_v1.py \
  src/scripts/analytics/build_runtime_governance_effectiveness_v1.py \
  src/scripts/run_market_pipeline.py \
  src/finam_core/pipelines/paper_pipeline.py

echo "RUNTIME_GOVERNANCE_POPULATION_STATUS_BEFORE"
/opt/finam-core/venv/bin/python src/scripts/analytics/build_runtime_governance_population_status_v1.py \
  --window-hours "${WINDOW_HOURS}"

for i in $(seq 1 "${RUNS}"); do
  echo "RUNTIME_GOVERNANCE_POPULATION_RUN_START run=${i}/${RUNS}"

  set +e
  timeout "$((RUN_SECS + 60))s" env \
    PYTHONPATH=src \
    EXECUTION_MODE=paper \
    RISK_SOFT=1 \
    EXIT_ON_FILL=1 \
    ENABLE_FILTER_ENGINE=1 \
    TRADEABILITY_GATE=range_atr_band \
    TRADEABILITY_MIN_RANGE_ATR=0 \
    TRADEABILITY_MAX_RANGE_ATR=999 \
    BR_ADAPTIVE_VOL_GATE_ENABLED=0 \
    ATR_MIN_PCT=0 \
    BR_COMPRESSION_WATCH_ENABLED=0 \
    TREND_STRENGTH_MIN=0 \
    IMPULSE_MIN=0 \
    PIPE_VOL_GATE_OK_LOG_EVERY_SEC=30 \
    PIPE_VOL_LOW_BLOCK_LOG_EVERY_SEC=30 \
    RUNTIME_GOVERNANCE_OBSERVATION_BYPASS_SESSION_PREOPEN=1 \
    /opt/finam-core/venv/bin/python src/scripts/run_market_pipeline.py \
      --symbol "${SYMBOL}" \
      --strategy "${STRATEGY}" \
      --run-secs "${RUN_SECS}" \
      --starting-cash "${STARTING_CASH}"

  PIPE_RC=$?
  set -e

  echo "RUNTIME_GOVERNANCE_POPULATION_RUN_DONE run=${i}/${RUNS} exit_code=${PIPE_RC}"

  /opt/finam-core/venv/bin/python src/scripts/analytics/build_runtime_governance_population_status_v1.py \
    --window-hours "${WINDOW_HOURS}"

  if [ "${PIPE_RC}" -ne 0 ] && [ "${PIPE_RC}" -ne 124 ]; then
    echo "RUNTIME_GOVERNANCE_POPULATION_RUN_WARN unexpected_exit_code=${PIPE_RC}"
  fi
done

echo "RUNTIME_GOVERNANCE_POPULATION_EFFECTIVENESS_AFTER"
/opt/finam-core/venv/bin/python src/scripts/analytics/build_runtime_governance_effectiveness_v1.py \
  --window-hours "${WINDOW_HOURS}"

echo "RUNTIME_GOVERNANCE_POPULATION_RUNNER_V1_OK"
