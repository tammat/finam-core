#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_GLOBAL_EDGE_DISCOVERY_V2_EXPANSION_PLAN ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/build_global_edge_discovery_v2_expansion_plan.py

OUT="$(PYTHONPATH=src python src/scripts/research/build_global_edge_discovery_v2_expansion_plan.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "reason=ranked_candidates_failed_robustness_and_walk_forward"
echo "$OUT" | grep -q "data_gap=futures_fx_no_replay_data"
echo "$OUT" | grep -q "timeframes_scope=M1,M5,M15,H1"
echo "$OUT" | grep -q "strategies_scope=BREAKOUT,MEAN_REVERSION,TREND_FOLLOWING,VOLATILITY_EXPANSION"
echo "$OUT" | grep -q "runtime_allowed=0"
echo "$OUT" | grep -q "execution_allowed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "orders_changed=0"
echo "$OUT" | grep -q "fills_changed=0"
echo "$OUT" | grep -q "VERDICT=GLOBAL_EDGE_DISCOVERY_V2_EXPANSION_PLAN_READY"

python - <<'PY'
import os
import psycopg2

db = os.getenv("DATABASE_URL", "postgresql:///finam_core")

with psycopg2.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT count(*)
            FROM analytics_global_edge_expansion_plan_v2
            WHERE plan_key='GLOBAL_EDGE_DISCOVERY_V2_EXPANSION_PLAN'
              AND runtime_allowed=false
              AND execution_allowed=false
              AND micro_live_allowed=false;
        """)
        total = cur.fetchone()[0]

assert total == 1

print("db_expansion_plan_ready=READY")
print("db_runtime_block_ready=READY")
PY

echo "VERDICT=TEST_GLOBAL_EDGE_DISCOVERY_V2_EXPANSION_PLAN_OK"
