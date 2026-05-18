#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_replay_batch.py \
  src/scripts/run_replay_campaign.py

python src/scripts/run_replay_batch.py --help >/dev/null

echo "OK: run_replay_batch moex compile"
