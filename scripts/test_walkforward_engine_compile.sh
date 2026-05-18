#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/walkforward_engine.py \
  src/scripts/run_walkforward_research.py

python src/scripts/run_walkforward_research.py --help >/dev/null

python src/scripts/run_walkforward_research.py \
  --research-id test-wf \
  --symbols SBER@MISX \
  --start-date 2024-01-01 \
  --end-date 2024-09-30 \
  --train-months 6 \
  --test-months 1 \
  --dry-run >/tmp/walkforward_test.log

grep -q "WALKFORWARD_START" /tmp/walkforward_test.log
grep -q "WALKFORWARD_WINDOW" /tmp/walkforward_test.log
grep -q "WALKFORWARD_DONE" /tmp/walkforward_test.log

echo "OK: walkforward engine compile"
