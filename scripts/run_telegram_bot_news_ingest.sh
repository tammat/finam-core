#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
source .venv/bin/activate
export PYTHONPATH=src

set -a
source .env
set +a

export ALL_PROXY="${TG_PROXY:-}"
export HTTPS_PROXY="${TG_PROXY:-}"
export HTTP_PROXY="${TG_PROXY:-}"

python -m finam_core.ai.telegram_bot_news_ingest
