#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
mkdir -p runtime/logs
if [[ -f deploy/env/.env ]]; then
  set -a
  # Единая DB-роль нужна дочерним DB-задачам для их узких checkpoint-таблиц.
  source deploy/env/.env
  set +a
fi
FINAM_DATABASE_URL="${DATABASE_URL:-postgresql:///finam_core}"
exec env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  DATABASE_URL=postgresql:///finam_core FINAM_DATABASE_URL="$FINAM_DATABASE_URL" \
  venv/bin/python src/scripts/run_db_job_scheduler_v1.py \
  >>runtime/logs/db-job-scheduler-v1.log 2>&1
