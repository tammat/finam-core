#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MULTI_TIMEFRAME_UNIVERSE_EXPANSION_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/build_multi_timeframe_universe_expansion_v1.py

OUT="$(PYTHONPATH=src python src/scripts/research/build_multi_timeframe_universe_expansion_v1.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "expanded_rows="
echo "$OUT" | grep -q "timeframes=M1,M5,M15,H1"
echo "$OUT" | grep -q "runtime_allowed=0"
echo "$OUT" | grep -q "execution_allowed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "orders_changed=0"
echo "$OUT" | grep -q "fills_changed=0"
echo "$OUT" | grep -q "VERDICT=MULTI_TIMEFRAME_UNIVERSE_EXPANSION_V1_READY"

python - <<'PY'
import os
import psycopg2

db = os.getenv("DATABASE_URL", "postgresql:///finam_core")

with psycopg2.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM analytics_global_edge_universe_timeframe_v2;")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT count(DISTINCT timeframe)
            FROM analytics_global_edge_universe_timeframe_v2;
        """)
        timeframes = cur.fetchone()[0]

        cur.execute("""
            SELECT count(*)
            FROM analytics_global_edge_universe_timeframe_v2
            WHERE runtime_allowed=true
               OR execution_allowed=true
               OR micro_live_allowed=true;
        """)
        allowed = cur.fetchone()[0]

assert total >= 28
assert timeframes == 4
assert allowed == 0

print("db_multi_timeframe_universe_ready=READY")
print("db_timeframes_ready=READY")
print("db_runtime_block_ready=READY")
PY

echo "VERDICT=TEST_MULTI_TIMEFRAME_UNIVERSE_EXPANSION_V1_OK"
