#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_runtime_shadow_validation_gold_v1.py

GOLD_SYMBOL="GDU6@RTSX" \
python3 src/scripts/research/build_runtime_shadow_validation_gold_v1.py \
  | tee /tmp/runtime_shadow_validation_gold_next_contract_v1.log

grep -q "RUNTIME SHADOW VALIDATION GOLD V1" /tmp/runtime_shadow_validation_gold_next_contract_v1.log
grep -q "symbol=GDU6@RTSX" /tmp/runtime_shadow_validation_gold_next_contract_v1.log
grep -q "DEDUP=enabled" /tmp/runtime_shadow_validation_gold_next_contract_v1.log
grep -q "RUNTIME_SHADOW_VALIDATION_GOLD_V1_1_DEDUP_OK" /tmp/runtime_shadow_validation_gold_next_contract_v1.log

echo "TEST_RUNTIME_SHADOW_VALIDATION_GOLD_NEXT_CONTRACT_V1_OK"
