#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/build_replay_closed_trades.py \
  src/finam_core/analytics/closed_trade_engine.py \
  src/finam_core/analytics/closed_trade_repository.py

python src/scripts/build_replay_closed_trades.py --help >/dev/null

echo "OK: build_replay_closed_trades compile"
