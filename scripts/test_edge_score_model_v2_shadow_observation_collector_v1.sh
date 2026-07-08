#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_COLLECTOR_V1 ==="

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_shadow_collector \
PYTHONDONTWRITEBYTECODE=0 \
PYTHONPATH=src \
python -m py_compile src/scripts/build_edge_score_model_v2_shadow_observation_collector.py

out=$(
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_shadow_collector \
  PYTHONDONTWRITEBYTECODE=0 \
  PYTHONPATH=src \
  python src/scripts/build_edge_score_model_v2_shadow_observation_collector.py
)

echo "$out"

echo "$out" | grep -q "unsafe_rows=0"
echo "$out" | grep -q "runtime_changed=0"
echo "$out" | grep -q "execution_changed=0"
echo "$out" | grep -q "orders_changed=0"
echo "$out" | grep -q "fills_changed=0"
echo "$out" | grep -q "micro_live_allowed=0"
echo "$out" | grep -q "VERDICT=EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_COLLECTOR_V1_READY"

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2_shadow_observation_v1
WHERE source_version='EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_COLLECTOR_V1';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2_shadow_observation_v1
WHERE source_version='EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_COLLECTOR_V1'
  AND (
      runtime_allowed <> 0
   OR execution_allowed <> 0
   OR micro_live_allowed <> 0
   OR order_seen <> 0
   OR fill_seen <> 0
  );
")

if [ "$rows" -lt 1 ]; then
  echo "NO_SHADOW_OBSERVATION_ROWS"
  exit 1
fi

if [ "$unsafe" != "0" ]; then
  echo "UNSAFE_SHADOW_OBSERVATION_ROWS=$unsafe"
  exit 1
fi

echo "shadow_rows=$rows"
echo "unsafe_rows=0"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_COLLECTOR_V1_OK"
