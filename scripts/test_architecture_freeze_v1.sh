#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/architecture/build_architecture_freeze_v1.py

python3 \
  src/scripts/architecture/build_architecture_freeze_v1.py \
  | tee /tmp/architecture_freeze_v1.log

grep -q "ARCHITECTURE FREEZE V1" /tmp/architecture_freeze_v1.log
grep -q "ARCH_FREEZE_STATE" /tmp/architecture_freeze_v1.log
grep -q "ARCHITECTURE_FREEZE_VERDICT" /tmp/architecture_freeze_v1.log
grep -q "ARCHITECTURE_FREEZE_V1_OK" /tmp/architecture_freeze_v1.log

echo TEST_ARCHITECTURE_FREEZE_V1_OK
