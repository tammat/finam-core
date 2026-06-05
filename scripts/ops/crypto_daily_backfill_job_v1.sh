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

if [ -z "${DATABASE_URL:-}" ]; then
  while IFS= read -r env_line; do
    env_line="${env_line#Environment=}"
    env_line="${env_line%\"}"
    env_line="${env_line#\"}"
    case "$env_line" in
      DATABASE_URL=*) export "$env_line" ;;
      PG*=*) export "$env_line" ;;
    esac
  done < <(systemctl cat finam-paper-pipeline.service 2>/dev/null | grep '^Environment=' || true)
fi

if [ -z "${DATABASE_URL:-}" ] && [ -r "/opt/finam-core/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . /opt/finam-core/.env
  set +a
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo "CRYPTO_DAILY_BACKFILL_FAILED reason=DATABASE_URL_NOT_SET"
  exit 1
fi

PY_BIN="/opt/finam-core/venv/bin/python"
if [ -x "/opt/finam-core/.venv/bin/python" ]; then
  PY_BIN="/opt/finam-core/.venv/bin/python"
fi

echo "=== CRYPTO DAILY BACKFILL JOB V1 ==="
date -Is

"$PY_BIN" src/scripts/research/binance_crypto_backfill_v1.py \
  --symbols BTCUSD,ETHUSD \
  --timeframes M1,M5 \
  --hours 30 \
  --apply

"$PY_BIN" src/scripts/observability/build_crypto_research_dashboard_v1.py

echo "CRYPTO_DAILY_BACKFILL_JOB_V1_OK"
