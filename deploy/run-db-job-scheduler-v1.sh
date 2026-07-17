#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
mkdir -p runtime/logs
exec env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 DATABASE_URL=postgresql:///finam_core \
  venv/bin/python src/scripts/run_db_job_scheduler_v1.py \
  >>runtime/logs/db-job-scheduler-v1.log 2>&1
