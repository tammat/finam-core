#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_strategy_identity_audit_v1.py

python3 src/scripts/research/build_strategy_identity_audit_v1.py \
  --symbol SBER@MISX \
  --strategy MOEX_SIMPLE_MOMENTUM \
  --timeframe D1 \
  | tee /tmp/sber_strategy_identity_audit_v1.log

python3 src/scripts/research/build_strategy_identity_audit_v1.py \
  --symbol PLZL@MISX \
  --strategy MOEX_SIMPLE_MOMENTUM \
  --timeframe D1 \
  | tee /tmp/plzl_strategy_identity_audit_v1.log

grep -q "STRATEGY_IDENTITY_AUDIT_V1_OK" /tmp/sber_strategy_identity_audit_v1.log
grep -q "STRATEGY_IDENTITY_AUDIT_V1_OK" /tmp/plzl_strategy_identity_audit_v1.log
grep -q "runtime_allow=0" /tmp/sber_strategy_identity_audit_v1.log
grep -q "execution_enabled=0" /tmp/plzl_strategy_identity_audit_v1.log

echo TEST_STRATEGY_IDENTITY_AUDIT_V1_OK
