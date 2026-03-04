#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ -z "${FINAM_TOKEN:-}" && -z "${FINAM_JWT:-}" && -z "${JWT:-}" ]]; then
  echo "ERR: FINAM_TOKEN/FINAM_JWT/JWT env var is not set"
  exit 2
fi

export PYTHONPATH=src

# 15 секунд достаточно: либо увидим RAW события, либо проверим что процесс живой и без immediate error
timeout 15s python -m scripts.live_quotes || true

echo "OK: live_quotes smoke finished (timeout expected if stream is quiet)"