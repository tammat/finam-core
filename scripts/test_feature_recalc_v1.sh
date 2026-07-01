#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_RECALC_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/build_feature_recalc_v1.py

OUT="$(PYTHONPATH=src python src/scripts/research/build_feature_recalc_v1.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "features_saved="
echo "$OUT" | grep -q "timeframe=M5"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "orders_changed=0"
echo "$OUT" | grep -q "fills_changed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "VERDICT=FEATURE_RECALC_V1_READY"

python - <<'PY'
import os
import psycopg2

db = os.getenv("DATABASE_URL", "postgresql:///finam_core")

with psycopg2.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM analytics_global_edge_features_v2;")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT count(*)
            FROM analytics_global_edge_features_v2
            WHERE timeframe='M5';
        """)
        m5 = cur.fetchone()[0]

assert total >= 7
assert m5 >= 7

print("db_features_ready=READY")
print("db_timeframe_ready=READY")
PY

echo "VERDICT=TEST_FEATURE_RECALC_V1_OK"
