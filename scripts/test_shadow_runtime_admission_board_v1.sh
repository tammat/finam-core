#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_shadow_runtime_admission_board_v1.py

python3 src/scripts/runtime/build_shadow_runtime_admission_board_v1.py \
  | tee /tmp/shadow_runtime_admission_board_v1.log

grep -q "SHADOW RUNTIME ADMISSION BOARD V1" /tmp/shadow_runtime_admission_board_v1.log
grep -q "GDU6@RTSX" /tmp/shadow_runtime_admission_board_v1.log
grep -q "LKOH@MISX" /tmp/shadow_runtime_admission_board_v1.log
grep -q "ADMIT_SHADOW_RUNTIME" /tmp/shadow_runtime_admission_board_v1.log
grep -q "SUMMARY_ROW admitted=2 rejected=3" /tmp/shadow_runtime_admission_board_v1.log
grep -q "runtime_allow=0" /tmp/shadow_runtime_admission_board_v1.log
grep -q "execution_enabled=0" /tmp/shadow_runtime_admission_board_v1.log
grep -q "SHADOW_RUNTIME_ADMISSION_BOARD_V1_OK" /tmp/shadow_runtime_admission_board_v1.log

echo TEST_SHADOW_RUNTIME_ADMISSION_BOARD_V1_OK
