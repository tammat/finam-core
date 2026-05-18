#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_replay_campaign.py \
  src/finam_core/replay/external_replay_adapter.py \
  src/finam_core/data/moex_candle_provider.py \
  src/finam_core/data/moex_symbol_resolver.py

python src/scripts/run_replay_campaign.py --help >/dev/null

echo "OK: run_replay_campaign moex compile"
