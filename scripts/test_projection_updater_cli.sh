#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

OUTPUT="$(bash scripts/update_projections.sh 1000)"

echo "${OUTPUT}"

grep -q "PROJECTION_UPDATE_OK" <<< "${OUTPUT}"

echo "PROJECTION_UPDATER_CLI_OK"
