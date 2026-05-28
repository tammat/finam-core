#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_SHADOW_OBSERVATION_PERSISTENCE_V1_START"

python -m py_compile \
  src/finam_core/analytics/runtime_shadow_observation_persistence_v1.py \
  src/scripts/analytics/build_runtime_shadow_observation_persistence_v1.py

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_runtime_shadow_observation_persistence_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "RUNTIME_SHADOW_OBSERVATION_PERSISTENCE_V1" "$TMP_LOG"
grep -q "RUNTIME_SHADOW_OBSERVATION_PERSISTENCE_STATUS" "$TMP_LOG"
grep -q "RUNTIME_SHADOW_OBSERVATION_PERSISTENCE_V1_OK" "$TMP_LOG"

psql "$DATABASE_URL" -c "
SELECT
    id,
    symbol,
    side,
    hour_msk,
    decay_state,
    shadow_block_candidate,
    raw_json->>'source' AS source
FROM runtime_shadow_observation_v1
ORDER BY id DESC
LIMIT 5;
"

echo "TEST_RUNTIME_SHADOW_OBSERVATION_PERSISTENCE_V1_OK"
