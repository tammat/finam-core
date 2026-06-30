#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

print("=== GOLD_SESSION_GUARD_SHADOW_EVENING_OBSERVATION_V1 ===")
print("mode=observation")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:

        cur.execute("""
        select
            count(*)::int as total_rows
        from runtime_guard_pre_signal_block_audit_v1
        where block_reason='gold_evening_session'
        """)
        total_rows = cur.fetchone()["total_rows"]

        cur.execute("""
        select
            count(*)::int as rows_24h
        from runtime_guard_pre_signal_block_audit_v1
        where block_reason='gold_evening_session'
          and created_at >= now() - interval '24 hour'
        """)
        rows_24h = cur.fetchone()["rows_24h"]

        cur.execute("""
        select
            symbol,
            strategy,
            timeframe,
            ts,
            block_type,
            block_reason
        from runtime_guard_pre_signal_block_audit_v1
        where block_reason='gold_evening_session'
        order by created_at desc
        limit 5
        """)
        latest = cur.fetchall()

print(f"audit_total={total_rows}")
print(f"audit_last_24h={rows_24h}")

print("\nLATEST_ROWS")

for r in latest:
    print(
        "AUDIT_ROW "
        f"symbol={r['symbol']} "
        f"strategy={r['strategy']} "
        f"timeframe={r['timeframe']} "
        f"ts={r['ts']} "
        f"block_type={r['block_type']} "
        f"block_reason={r['block_reason']}"
    )

print("\nVERDICT=GOLD_SESSION_GUARD_SHADOW_EVENING_OBSERVATION_READY")
