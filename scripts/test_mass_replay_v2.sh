#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MASS_REPLAY_V2 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/build_mass_replay_v2.py

OUT="$(PYTHONPATH=src python src/scripts/research/build_mass_replay_v2.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "replay_rows="
echo "$OUT" | grep -q "strategy=V2_BASELINE_BREAKOUT"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "orders_changed=0"
echo "$OUT" | grep -q "fills_changed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "VERDICT=MASS_REPLAY_V2_READY"

python - <<'PY'
import os
import psycopg2

db = os.getenv("DATABASE_URL", "postgresql:///finam_core")

with psycopg2.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM analytics_global_edge_replay_v2;")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT count(*)
            FROM analytics_global_edge_replay_v2
            WHERE strategy_name='V2_BASELINE_BREAKOUT';
        """)
        baseline = cur.fetchone()[0]

assert total >= 7
assert baseline >= 7

print("db_replay_ready=READY")
print("db_strategy_ready=READY")
PY

echo "VERDICT=TEST_MASS_REPLAY_V2_OK"
