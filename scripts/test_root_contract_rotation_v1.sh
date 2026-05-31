#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_ROOT_CONTRACT_ROTATION_V1_START"

python -m py_compile src/scripts/ops/build_root_contract_rotation_v1.py

python src/scripts/ops/build_root_contract_rotation_v1.py \
  --br BRN6@RTSX \
  --ng NGN6@RTSX | tee /tmp/root_contract_rotation_v1.conf

grep -q "BRN6@RTSX" /tmp/root_contract_rotation_v1.conf
grep -q "NGN6@RTSX" /tmp/root_contract_rotation_v1.conf
! grep -q "BRM6@RTSX" /tmp/root_contract_rotation_v1.conf
! grep -q "NGK6@RTSX" /tmp/root_contract_rotation_v1.conf

echo "TEST_ROOT_CONTRACT_ROTATION_V1_OK"
