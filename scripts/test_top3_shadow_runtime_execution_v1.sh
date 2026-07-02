#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TOP3_SHADOW_RUNTIME_EXECUTION_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/build_top3_shadow_runtime_execution_v1.py

OUT="$(PYTHONPATH=src python src/scripts/research/build_top3_shadow_runtime_execution_v1.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=shadow_runtime_only"
echo "$OUT" | grep -q "shadow_execution_rows=3"
echo "$OUT" | grep -q "shadow_status=SHADOW_ACTIVE"
echo "$OUT" | grep -q "virtual_signal_status=VIRTUAL_SIGNAL_READY"
echo "$OUT" | grep -q "virtual_order_status=VIRTUAL_ORDER_READY"
echo "$OUT" | grep -q "virtual_fill_status=VIRTUAL_FILL_READY"
echo "$OUT" | grep -q "risk_status=RISK_OK"
echo "$OUT" | grep -q "runtime_allowed=0"
echo "$OUT" | grep -q "execution_allowed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "orders_changed=0"
echo "$OUT" | grep -q "fills_changed=0"
echo "$OUT" | grep -q "VERDICT=TOP3_SHADOW_RUNTIME_EXECUTION_V1_READY"

python - <<'PY'
import os
import psycopg2

db = os.getenv("DATABASE_URL", "postgresql:///finam_core")

with psycopg2.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM analytics_global_edge_top3_shadow_runtime_execution_v1;")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT count(*)
            FROM analytics_global_edge_top3_shadow_runtime_execution_v1
            WHERE shadow_status='SHADOW_ACTIVE'
              AND virtual_signal_status='VIRTUAL_SIGNAL_READY'
              AND virtual_order_status='VIRTUAL_ORDER_READY'
              AND virtual_fill_status='VIRTUAL_FILL_READY'
              AND risk_status='RISK_OK';
        """)
        active = cur.fetchone()[0]

        cur.execute("""
            SELECT count(*)
            FROM analytics_global_edge_top3_shadow_runtime_execution_v1
            WHERE runtime_allowed=true
               OR execution_allowed=true
               OR micro_live_allowed=true;
        """)
        allowed = cur.fetchone()[0]

assert total >= 3
assert active >= 3
assert allowed == 0

print("db_top3_shadow_execution_ready=READY")
print("db_virtual_events_ready=READY")
print("db_runtime_block_ready=READY")
PY

echo "VERDICT=TEST_TOP3_SHADOW_RUNTIME_EXECUTION_V1_OK"
