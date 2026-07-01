#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FORENSIC_ANALYSIS_V2 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/build_forensic_analysis_v2.py

OUT="$(PYTHONPATH=src python src/scripts/research/build_forensic_analysis_v2.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "forensic_rows="
echo "$OUT" | grep -q "runtime_allowed=0"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "orders_changed=0"
echo "$OUT" | grep -q "fills_changed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "VERDICT=FORENSIC_ANALYSIS_V2_READY"

python - <<'PY'
import os
import psycopg2

db = os.getenv("DATABASE_URL", "postgresql:///finam_core")

with psycopg2.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM analytics_global_edge_forensic_v2;")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT count(*)
            FROM analytics_global_edge_forensic_v2
            WHERE runtime_allowed = true;
        """)
        runtime_allowed = cur.fetchone()[0]

        cur.execute("""
            SELECT count(*)
            FROM analytics_global_edge_forensic_v2
            WHERE forensic_status IN ('FORENSIC_PASS', 'FORENSIC_REJECT');
        """)
        classified = cur.fetchone()[0]

assert total >= 7
assert classified >= 7
assert runtime_allowed == 0

print("db_forensic_ready=READY")
print("db_classification_ready=READY")
print("db_runtime_block_ready=READY")
PY

echo "VERDICT=TEST_FORENSIC_ANALYSIS_V2_OK"
