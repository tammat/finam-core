#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_usdrub_loss_tail_filter_v1.py

python3 src/scripts/research/build_usdrub_loss_tail_filter_v1.py \
  | tee /tmp/usdrub_loss_tail_filter_v1.log

grep -q "USDRUB LOSS TAIL FILTER V1" /tmp/usdrub_loss_tail_filter_v1.log
grep -q "RAW_ROW" /tmp/usdrub_loss_tail_filter_v1.log
grep -q "FILTER_ROW" /tmp/usdrub_loss_tail_filter_v1.log
grep -q "loss_cap=-2.0" /tmp/usdrub_loss_tail_filter_v1.log
grep -q "tail_trades=" /tmp/usdrub_loss_tail_filter_v1.log
grep -q "pnl_improvement=" /tmp/usdrub_loss_tail_filter_v1.log
grep -q "runtime_allow=0" /tmp/usdrub_loss_tail_filter_v1.log
grep -q "execution_enabled=0" /tmp/usdrub_loss_tail_filter_v1.log
grep -q "USDRUB_LOSS_TAIL_FILTER_V1_OK" /tmp/usdrub_loss_tail_filter_v1.log

echo TEST_USDRUB_LOSS_TAIL_FILTER_V1_OK
