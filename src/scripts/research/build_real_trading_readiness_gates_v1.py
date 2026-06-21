#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import psycopg
from psycopg.rows import dict_row


def env_flag(name: str) -> str:
    return str(os.getenv(name, "0"))


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    failures = []

    runtime_allow = env_flag("RUNTIME_ALLOW_TRADING")
    execution_enabled = env_flag("EXECUTION_ENABLED")
    real_trading_enabled = env_flag("REAL_TRADING_ENABLED")

    if runtime_allow != "0":
        failures.append("RUNTIME_ALLOW_TRADING_NOT_ZERO")
    if execution_enabled != "0":
        failures.append("EXECUTION_ENABLED_NOT_ZERO")
    if real_trading_enabled != "0":
        failures.append("REAL_TRADING_ENABLED_NOT_ZERO")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select count(*)::int as c
                from runtime_active_universe
                where is_enabled = true
            """)
            runtime_active = cur.fetchone()["c"]

            cur.execute("""
                select count(*)::int as c
                from runtime_active_universe
                where is_enabled = true
                  and symbol like '%@MISX'
            """)
            active_equities = cur.fetchone()["c"]

            cur.execute("""
                select count(*)::int as c
                from market_bars
                where symbol in ('IMOEX','RTSI')
                  and timeframe in ('M1','M5')
            """)
            index_bars = cur.fetchone()["c"]

            cur.execute("""
                select count(*)::int as c
                from analytics_multi_asset_compression_snapshot_v1
            """)
            compression_snapshots = cur.fetchone()["c"]

            cur.execute("""
                select count(*)::int as c
                from analytics_multi_asset_compression_follow_through_v1
            """)
            compression_follow_rows = cur.fetchone()["c"]

    if runtime_active < 8:
        failures.append("RUNTIME_ACTIVE_UNIVERSE_TOO_SMALL")
    if active_equities < 8:
        failures.append("ACTIVE_EQUITIES_LT_8")
    if index_bars <= 0:
        failures.append("INDEX_MARKET_BARS_MISSING")
    if compression_snapshots <= 0:
        failures.append("COMPRESSION_HISTORY_MISSING")
    if compression_follow_rows <= 0:
        failures.append("COMPRESSION_FOLLOW_THROUGH_MISSING")

    verdict = "REAL_TRADING_READINESS_BLOCKED" if failures else "LIMITED_PAPER_READY"

    print("=== REAL_TRADING_READINESS_GATES_V1 ===")
    print(f"runtime_allow={runtime_allow}")
    print(f"execution_enabled={execution_enabled}")
    print(f"real_trading_enabled={real_trading_enabled}")
    print(f"runtime_active={runtime_active}")
    print(f"active_equities={active_equities}")
    print(f"index_bars={index_bars}")
    print(f"compression_snapshots={compression_snapshots}")
    print(f"compression_follow_rows={compression_follow_rows}")
    print(f"failures={','.join(failures) if failures else 'NONE'}")
    print(f"VERDICT={verdict}")
    print("TEST_REAL_TRADING_READINESS_GATES_V1_OK")

    return 0 if verdict == "LIMITED_PAPER_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
