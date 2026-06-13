#!/usr/bin/env python3
from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras

STALE_MINUTES = 1440

SOURCE_TABLES = {
    "GDU6@RTSX": "runtime_shadow_gold_signals",
    "LKOH@MISX": "lkoh_shadow_signals",
}

DDL = """
CREATE TABLE IF NOT EXISTS shadow_runtime_signal_monitor (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    source text,
    signal_source_table text,
    signals_total bigint,
    signals_24h bigint,
    first_signal_ts timestamptz,
    last_signal_ts timestamptz,
    last_signal_age_minutes numeric,
    monitor_status text NOT NULL,
    shadow_runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_shadow_runtime_signal_monitor_symbol_created
ON shadow_runtime_signal_monitor(symbol, created_at DESC);
"""

SQL_WATCHLIST = """
SELECT DISTINCT ON (symbol)
    symbol,
    source,
    watch_status,
    shadow_runtime_allowed,
    execution_enabled
FROM shadow_runtime_watchlist
ORDER BY symbol, id DESC;
"""

SQL_TABLE_EXISTS = """
SELECT EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='public'
      AND table_name=%s
);
"""

def table_exists(cur, table_name: str | None) -> bool:
    if not table_name:
        return False
    cur.execute(SQL_TABLE_EXISTS, (table_name,))
    return bool(cur.fetchone()["exists"])

def signal_stats(cur, table_name: str, symbol: str) -> dict:
    cur.execute(
        f"""
        SELECT
            COUNT(*)::bigint AS signals_total,
            COUNT(*) FILTER (
                WHERE signal_ts >= now() - interval '24 hours'
            )::bigint AS signals_24h,
            MIN(signal_ts) AS first_signal_ts,
            MAX(signal_ts) AS last_signal_ts,
            EXTRACT(EPOCH FROM (now() - MAX(signal_ts))) / 60.0
                AS last_signal_age_minutes
        FROM {table_name}
        WHERE symbol=%s;
        """,
        (symbol,),
    )
    return dict(cur.fetchone())

def main() -> int:
    print("=== SHADOW RUNTIME SIGNAL MONITOR V1 ===")
    print("mode=signal_monitor")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    healthy = 0
    stale = 0
    no_signals = 0
    missing = 0
    skipped = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL_WATCHLIST)
            rows = cur.fetchall()

            print("MONITOR_ROWS")

            for row in rows:
                symbol = row["symbol"]
                source_table = SOURCE_TABLES.get(symbol)

                stats = {
                    "signals_total": 0,
                    "signals_24h": 0,
                    "first_signal_ts": None,
                    "last_signal_ts": None,
                    "last_signal_age_minutes": None,
                }

                if row["watch_status"] != "WATCH_SHADOW_RUNTIME":
                    status = "SKIP"
                    skipped += 1
                elif not table_exists(cur, source_table):
                    status = "SOURCE_MISSING"
                    missing += 1
                else:
                    stats = signal_stats(cur, source_table, symbol)
                    age = stats["last_signal_age_minutes"]

                    if int(stats["signals_total"] or 0) == 0:
                        status = "NO_SIGNALS"
                        no_signals += 1
                    elif age is not None and float(age) > STALE_MINUTES:
                        status = "STALE"
                        stale += 1
                    else:
                        status = "HEALTHY"
                        healthy += 1

                payload = {
                    "symbol": symbol,
                    "source": row["source"],
                    "signal_source_table": source_table,
                    "watch_status": row["watch_status"],
                    "signals_total": stats["signals_total"],
                    "signals_24h": stats["signals_24h"],
                    "first_signal_ts": str(stats["first_signal_ts"]) if stats["first_signal_ts"] else None,
                    "last_signal_ts": str(stats["last_signal_ts"]) if stats["last_signal_ts"] else None,
                    "last_signal_age_minutes": float(stats["last_signal_age_minutes"]) if stats["last_signal_age_minutes"] is not None else None,
                    "monitor_status": status,
                    "shadow_runtime_allowed": bool(row["shadow_runtime_allowed"]),
                    "execution_enabled": False,
                }

                cur.execute(
                    """
                    INSERT INTO shadow_runtime_signal_monitor (
                        symbol,
                        source,
                        signal_source_table,
                        signals_total,
                        signals_24h,
                        first_signal_ts,
                        last_signal_ts,
                        last_signal_age_minutes,
                        monitor_status,
                        shadow_runtime_allowed,
                        execution_enabled,
                        raw_json
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,%s::jsonb)
                    """,
                    (
                        symbol,
                        row["source"],
                        source_table,
                        stats["signals_total"],
                        stats["signals_24h"],
                        stats["first_signal_ts"],
                        stats["last_signal_ts"],
                        stats["last_signal_age_minutes"],
                        status,
                        bool(row["shadow_runtime_allowed"]),
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                print(
                    "MONITOR_ROW "
                    f"symbol={symbol} "
                    f"source_table={source_table} "
                    f"signals_total={stats['signals_total']} "
                    f"signals_24h={stats['signals_24h']} "
                    f"last_signal_ts={stats['last_signal_ts']} "
                    f"last_signal_age_minutes={stats['last_signal_age_minutes']} "
                    f"monitor_status={status} "
                    f"shadow_runtime_allowed={int(bool(row['shadow_runtime_allowed']))} "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(
        "SUMMARY_ROW "
        f"healthy={healthy} "
        f"stale={stale} "
        f"no_signals={no_signals} "
        f"missing={missing} "
        f"skipped={skipped}"
    )
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_SIGNAL_MONITOR_READY")
    print("SHADOW_RUNTIME_SIGNAL_MONITOR_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
