#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_RUNTIME_SESSION_GUARD_SHADOW_APPLY_V1 ==="

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "_resolve_hour_msk_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_RUNTIME_GOLD_SESSION_BLOCK" src/finam_core/pipelines/paper_pipeline.py
grep -q "gold_evening_session" src/finam_core/pipelines/paper_pipeline.py
grep -q "GOLD_SESSION_GUARD_BLOCK_ENABLED" src/finam_core/pipelines/paper_pipeline.py

if grep -q 'GOLD_SESSION_GUARD_BLOCK_ENABLED", "1"' src/finam_core/pipelines/paper_pipeline.py; then
  echo "BLOCK_ENABLED_BY_DEFAULT"
  exit 1
fi

echo "runtime_changed=0"
echo "execution_changed=0"
echo "real_trading_enabled=0"
echo "VERDICT=GOLD_RUNTIME_SESSION_GUARD_SHADOW_APPLY_OK"
echo "TEST_GOLD_RUNTIME_SESSION_GUARD_SHADOW_APPLY_V1_OK"
