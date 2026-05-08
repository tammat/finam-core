#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

if [ ! -f /opt/finam-core/.env.paper_safe ]; then
  echo "ENV_FILE_NOT_FOUND /opt/finam-core/.env.paper_safe"
  exit 1
fi

set -a
. /opt/finam-core/.env.paper_safe
set +a

export PYTHONPATH=src
export FINAM_TOKEN="${FINAM_TOKEN:-${FINAM_SECRET:-}}"

echo "SYSTEMD_POSITION_SYNC_ENV account=${FINAM_ACCOUNT_ID:-} token_len=${#FINAM_TOKEN}"

if [ -z "${FINAM_ACCOUNT_ID:-}" ]; then
  echo "FINAM_ACCOUNT_ID_EMPTY"
  exit 1
fi

if [ -z "${FINAM_TOKEN:-}" ]; then
  echo "FINAM_TOKEN_EMPTY"
  exit 1
fi

exec /opt/finam-core/venv/bin/python -m scripts.sync_finam_real_positions
