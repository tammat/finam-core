#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_gold_next_contract_replay_v1.py

python3 src/scripts/research/build_gold_next_contract_replay_v1.py \
  | tee /tmp/gold_next_contract_replay_v1.log

grep -q "GOLD NEXT CONTRACT REPLAY V1" /tmp/gold_next_contract_replay_v1.log
grep -q "NEXT_CONTRACT_ROWS" /tmp/gold_next_contract_replay_v1.log
grep -q "NEXT_CONTRACT_ROW symbol=GDM6@RTSX" /tmp/gold_next_contract_replay_v1.log
grep -q "NEXT_CONTRACT_ROW symbol=GDU6@RTSX" /tmp/gold_next_contract_replay_v1.log
grep -q "TRANSFER_ROW" /tmp/gold_next_contract_replay_v1.log
grep -q "GOLD_NEXT_CONTRACT_REPLAY_V1_OK" /tmp/gold_next_contract_replay_v1.log

echo "TEST_GOLD_NEXT_CONTRACT_REPLAY_V1_OK"
