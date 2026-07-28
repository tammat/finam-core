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

WINDOW_HOURS="${WINDOW_HOURS:-168}"

echo "RUNTIME_GOVERNANCE_POPULATION_RUNNER_V1_START"
echo "window_hours=${WINDOW_HOURS}"

/opt/finam-core/venv/bin/python -m py_compile \
  src/scripts/analytics/build_runtime_governance_population_status_v1.py \
  src/scripts/analytics/build_runtime_governance_effectiveness_v1.py \
  src/scripts/analytics/export_guard_decisions_v1.py

echo "RUNTIME_GOVERNANCE_POPULATION_STATUS_BEFORE"
/opt/finam-core/venv/bin/python src/scripts/analytics/build_runtime_governance_population_status_v1.py \
  --window-hours "${WINDOW_HOURS}"

echo "RUNTIME_GOVERNANCE_POPULATION_EFFECTIVENESS_AFTER"
/opt/finam-core/venv/bin/python src/scripts/analytics/build_runtime_governance_effectiveness_v1.py \
  --window-hours "${WINDOW_HOURS}"

echo "RUNTIME_GOVERNANCE_GUARD_SNAPSHOT_EXPORT"
/opt/finam-core/venv/bin/python src/scripts/analytics/export_guard_decisions_v1.py

echo "RUNTIME_GOVERNANCE_POPULATION_RUNNER_V1_OK"
