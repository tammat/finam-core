#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_replay_batch.py
python src/scripts/run_replay_batch.py --help >/dev/null

python src/scripts/run_replay_batch.py \
  --batch-id test-batch \
  --campaigns 1 \
  --symbols BRM6@RTSX \
  --run-secs 1 \
  --dry-run >/tmp/replay_batch_test.log

grep -q "REPLAY_BATCH_START" /tmp/replay_batch_test.log
grep -q "REPLAY_BATCH_DONE" /tmp/replay_batch_test.log

echo "OK: run_replay_batch compile"
