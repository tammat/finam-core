#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
mkdir -p runtime/logs
exec nice -n 10 ionice -c 2 -n 5 \
  env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 DATABASE_URL=postgresql:///finam_core \
  RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
  venv/bin/python src/scripts/run_forward_pass_shadow_observer_v2.py \
  >>runtime/logs/forward-pass-shadow-observer-v2.log 2>&1
