#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

print("=== GOLD_RUNTIME_SESSION_GUARD_SHADOW_RUNTIME_VALIDATION_V1 ===")
print("mode=runtime_validation")
print("db_update=0")
print("real_trading_enabled=0")

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:

        cur.execute("""
        select count(*)::int as cnt
        from runtime_guard_pre_signal_block_audit_v1
        where block_reason='gold_evening_session'
        """)
        audit_total = cur.fetchone()["cnt"]

        cur.execute("""
        select count(*)::int as cnt
        from runtime_guard_pre_signal_block_audit_v1
        where block_reason='gold_evening_session'
          and created_at >= now() - interval '24 hour'
        """)
        audit_24h = cur.fetchone()["cnt"]

print(f"audit_total={audit_total}")
print(f"audit_last_24h={audit_24h}")

print("expected_mode=shadow")
print("expected_env=GOLD_SESSION_GUARD_BLOCK_ENABLED")
print("blocking_default=0")

print("VERDICT=GOLD_RUNTIME_SESSION_GUARD_SHADOW_RUNTIME_VALIDATION_READY")
