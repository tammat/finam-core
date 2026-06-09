#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_runtime_contract_governor_snapshot_v1.py

python3 src/scripts/analytics/build_runtime_contract_governor_snapshot_v1.py \
  | tee /tmp/runtime_contract_governor_snapshot_v1.log

grep -q "RUNTIME CONTRACT GOVERNOR SNAPSHOT V1" /tmp/runtime_contract_governor_snapshot_v1.log
grep -q "SNAPSHOT_ROWS" /tmp/runtime_contract_governor_snapshot_v1.log
grep -q "SNAPSHOT_ROW root=BR" /tmp/runtime_contract_governor_snapshot_v1.log
grep -q "SNAPSHOT_ROW root=NG" /tmp/runtime_contract_governor_snapshot_v1.log
grep -q "RUNTIME_CONTRACT_GOVERNOR_SNAPSHOT_V1_OK" /tmp/runtime_contract_governor_snapshot_v1.log

echo "TEST_RUNTIME_CONTRACT_GOVERNOR_SNAPSHOT_V1_OK"
