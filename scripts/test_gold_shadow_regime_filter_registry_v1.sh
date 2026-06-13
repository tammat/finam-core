#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_gold_shadow_regime_filter_registry_v1.py

python3 src/scripts/research/build_gold_shadow_regime_filter_registry_v1.py \
  | tee /tmp/gold_shadow_regime_filter_registry_v1.log

grep -q "GOLD_SHADOW_REGIME_FILTER_REGISTRY_V1_OK" /tmp/gold_shadow_regime_filter_registry_v1.log
grep -q "mandatory_filter=gold_shadow_regime_filter_v1" /tmp/gold_shadow_regime_filter_registry_v1.log
grep -q "runtime_allowed=0" /tmp/gold_shadow_regime_filter_registry_v1.log
grep -q "execution_enabled=0" /tmp/gold_shadow_regime_filter_registry_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    status,
    runtime_allowed,
    execution_enabled,
    reason,
    raw_json->'mandatory_filters'->'gold_shadow_regime_filter_v1'->>'rule' AS filter_rule
FROM runtime_candidate_registry
WHERE symbol='GDU6@RTSX';
" | tee /tmp/gold_shadow_regime_filter_registry_db_v1.log

grep -q "up_impulse_sell_block" /tmp/gold_shadow_regime_filter_registry_db_v1.log
grep -q " f " /tmp/gold_shadow_regime_filter_registry_db_v1.log

echo TEST_GOLD_SHADOW_REGIME_FILTER_REGISTRY_V1_OK
