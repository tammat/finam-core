#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_RANKING_V2 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/build_edge_ranking_v2.py

OUT="$(PYTHONPATH=src python src/scripts/research/build_edge_ranking_v2.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "ranking_rows="
echo "$OUT" | grep -q "candidate_status=CANDIDATE"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "orders_changed=0"
echo "$OUT" | grep -q "fills_changed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "VERDICT=EDGE_RANKING_V2_READY"

python - <<'PY'
import os
import psycopg2

db = os.getenv("DATABASE_URL", "postgresql:///finam_core")

with psycopg2.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM analytics_global_edge_ranking_v2;")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT count(*)
            FROM analytics_global_edge_ranking_v2
            WHERE rank_no >= 1;
        """)
        ranked = cur.fetchone()[0]

assert total >= 7
assert ranked >= 7

print("db_ranking_ready=READY")
print("db_rank_ready=READY")
PY

echo "VERDICT=TEST_EDGE_RANKING_V2_OK"
