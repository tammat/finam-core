#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python src/scripts/analytics/build_intraday_pnl.py \
  --date "$(TZ=Europe/Moscow date +%F)" \
  --migrate \
  --save
