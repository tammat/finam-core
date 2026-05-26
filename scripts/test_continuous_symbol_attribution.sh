#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/contracts/continuous_contract_resolver.py \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/storage/postgres.py \
  src/finam_core/analytics/trade_context_snapshot_repository.py \
  src/scripts/replay_br_pipeline.py

python - <<'PY'
from finam_core.contracts.continuous_contract_resolver import ContinuousContractResolver

assert ContinuousContractResolver.resolve("BRM6@RTSX") == "BR_CONT"
assert ContinuousContractResolver.resolve("BRN6@RTSX") == "BR_CONT"
print("CONTINUOUS_CONTRACT_RESOLVER_OK")
PY

grep -q "continuous_symbol" src/finam_core/pipelines/paper_pipeline.py
grep -q "continuous_symbol" src/finam_core/storage/postgres.py
grep -q "continuous_symbol" src/finam_core/analytics/trade_context_snapshot_repository.py
grep -q "continuous_symbol" src/scripts/replay_br_pipeline.py

echo "CONTINUOUS_SYMBOL_ATTRIBUTION_OK"
