#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REGIME_MATRIX_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/build_regime_matrix_v1.py

OUT="$(PYTHONPATH=src python src/scripts/research/build_regime_matrix_v1.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "regime_matrix_rows="
echo "$OUT" | grep -q "regimes=TREND,RANGE,COMPRESSION,HIGH_VOLATILITY,LOW_VOLATILITY"
echo "$OUT" | grep -q "runtime_allowed=0"
echo "$OUT" | grep -q "execution_allowed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "orders_changed=0"
echo "$OUT" | grep -q "fills_changed=0"
echo "$OUT" | grep -q "VERDICT=REGIME_MATRIX_V1_READY"

python - <<'PY'
import os
import psycopg2

db = os.getenv("DATABASE_URL", "postgresql:///finam_core")

with psycopg2.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM analytics_global_edge_regime_matrix_v2;")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT count(DISTINCT regime)
            FROM analytics_global_edge_regime_matrix_v2;
        """)
        regimes = cur.fetchone()[0]

        cur.execute("""
            SELECT count(*)
            FROM analytics_global_edge_regime_matrix_v2
            WHERE runtime_allowed=true
               OR execution_allowed=true
               OR micro_live_allowed=true;
        """)
        allowed = cur.fetchone()[0]

assert total >= 560
assert regimes == 5
assert allowed == 0

print("db_regime_matrix_ready=READY")
print("db_regimes_ready=READY")
print("db_runtime_block_ready=READY")
PY

echo "VERDICT=TEST_REGIME_MATRIX_V1_OK"
