#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_parameter_sweep.py
python src/scripts/run_parameter_sweep.py --help >/dev/null

python src/scripts/run_parameter_sweep.py \
  --sweep-id test-sweep \
  --symbols SBER@MISX \
  --date-from 2025-05-01 \
  --date-to 2025-05-31 \
  --stop-pcts 0.01 \
  --take-pcts 0.02 \
  --holding-bars 1 \
  --dry-run >/tmp/parameter_sweep_test.log

grep -q "PARAM_SWEEP_START" /tmp/parameter_sweep_test.log
grep -q "PARAM_SWEEP_RUN" /tmp/parameter_sweep_test.log
grep -q "PARAM_SWEEP_DONE" /tmp/parameter_sweep_test.log

echo "OK: run_parameter_sweep compile"
