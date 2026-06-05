#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

if [ -z "${DATABASE_URL:-}" ]; then
  ENV_FILES=$(systemctl cat finam-paper-pipeline.service 2>/dev/null | sed -n 's/^EnvironmentFile=-\?//p' || true)
  for env_file in $ENV_FILES; do
    if [ -r "$env_file" ]; then
      set -a
      # shellcheck disable=SC1090
      . "$env_file"
      set +a
    fi
  done
fi

if [ -z "${DATABASE_URL:-}" ] && [ -r "/opt/finam-core/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . /opt/finam-core/.env
  set +a
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo "FEATURE_STORE_DAILY_REBUILD_FAILED reason=DATABASE_URL_NOT_SET"
  exit 1
fi

PY_BIN="/opt/finam-core/venv/bin/python"
if [ -x "/opt/finam-core/.venv/bin/python" ]; then
  PY_BIN="/opt/finam-core/.venv/bin/python"
fi

echo "=== FEATURE STORE DAILY REBUILD JOB V1 ==="
date -Is

"$PY_BIN" src/scripts/research/rebuild_feature_store_v1.py \
  --symbols BRN6@RTSX,NGN6@RTSX,USDRUBF@RTSX,BTCUSD,ETHUSD \
  --timeframes M1,M5 \
  --limit 5000

"$PY_BIN" src/scripts/observability/build_crypto_feature_dashboard_v1.py

echo "FEATURE_STORE_DAILY_REBUILD_JOB_V1_OK"
