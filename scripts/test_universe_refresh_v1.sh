#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_UNIVERSE_REFRESH_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/build_universe_refresh_v1.py

OUT="$(PYTHONPATH=src python src/scripts/research/build_universe_refresh_v1.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "universe_rows="
echo "$OUT" | grep -q "asset_classes=Фьючерсы,Акции,Валюта"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "orders_changed=0"
echo "$OUT" | grep -q "fills_changed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "VERDICT=UNIVERSE_REFRESH_V1_READY"

python - <<'PY'
import os
import psycopg2

db = os.getenv("DATABASE_URL", "postgresql:///finam_core")

with psycopg2.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM analytics_global_edge_universe_v2;")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT count(DISTINCT asset_class)
            FROM analytics_global_edge_universe_v2;
        """)
        asset_classes = cur.fetchone()[0]

assert total >= 7
assert asset_classes >= 3

print("db_universe_ready=READY")
print("db_asset_classes_ready=READY")
PY

echo "VERDICT=TEST_UNIVERSE_REFRESH_V1_OK"
