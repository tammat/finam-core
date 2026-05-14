#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
source .venv/bin/activate
export PYTHONPATH=src

set -a
source .env
set +a

python -m finam_core.ai.telethon_news_ingest
