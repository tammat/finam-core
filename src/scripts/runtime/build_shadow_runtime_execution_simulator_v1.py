#!/usr/bin/env python3
from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras

SOURCE_TABLES = {
    "LKOH@MISX": "lkoh_shadow_signals",
    "GDU6@RTSX": "runtime_shadow_gold_signals",
}

DDL = """
CREATE TABLE IF NOT EXISTS shadow_runtime_execution_simulator (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    source text,
    readiness_status text,
    signal_source_table text,
    signals_seen bigint,
    virtual_entries bigint,
    virtual_exits bigint,
    virtual_pnl numeric,
    winrate numeric,
    expectancy numeric,
    simulator_status text NOT NULL,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_shadow_runtime_execution_simulator_symbol
ON shadow_runtime_execution_simulator(symbol, created_at DESC);
"""

SQL_READINESS = """
SELECT DISTINCT ON (symbol)
    symbol,
    source,
    readiness_status,
    readiness_reason
FROM shadow_runtime_readiness_board
ORDER BY symbol, id DESC;
"""

def table_exists(cur, table_name: str | None) -> bool:
    if not table_name:
        return False
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema='public'
              AND table_name=%s
        );
        """,
        (table_name,),
    )
    return bool(cur.fetchone()["exists"])

def signal_count(cur, table_name: str, symbol: str) -> int:
    cur.execute(
        f"SELECT COUNT(*)::bigint AS cnt FROM {table_name} WHERE symbol=%s;",
        (symbol,),
    )
    return int(cur.fetchone()["cnt"] or 0)

def main() -> int:
    print("=== SHADOW RUNTIME EXECUTION SIMULATOR V1 ===")
    print("mode=execution_simulator")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    active = 0
    stale = 0
    blocked = 0
    no_signals = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL_READINESS)
            rows = cur.fetchall()

            print("SIMULATOR_ROWS")

            for row in rows:
                symbol = row["symbol"]
                source_table = SOURCE_TABLES.get(symbol)
                signals_seen = 0
                virtual_entries = 0
                virtual_exits = 0
                virtual_pnl = None
                winrate = None
                expectancy = None

                if row["readiness_status"] == "READY_FOR_SHADOW_RUNTIME":
                    if not table_exists(cur, source_table):
                        status = "SOURCE_MISSING"
                        blocked += 1
                    else:
                        signals_seen = signal_count(cur, source_table, symbol)
                        if signals_seen > 0:
                            status = "ACTIVE"
                            virtual_entries = signals_seen
                            virtual_exits = signals_seen
                            active += 1
                        else:
                            status = "NO_SIGNALS"
                            no_signals += 1

                elif row["readiness_status"] == "STALE_NEEDS_REFRESH":
                    status = "SKIP_STALE_SOURCE"
                    stale += 1

                else:
                    status = "BLOCKED"
                    blocked += 1

                payload = {
                    "symbol": symbol,
                    "source": row["source"],
                    "readiness_status": row["readiness_status"],
                    "readiness_reason": row["readiness_reason"],
                    "signal_source_table": source_table,
                    "signals_seen": signals_seen,
                    "virtual_entries": virtual_entries,
                    "virtual_exits": virtual_exits,
                    "virtual_pnl": virtual_pnl,
                    "winrate": winrate,
                    "expectancy": expectancy,
                    "simulator_status": status,
                    "runtime_allowed": False,
                    "execution_enabled": False,
                }

                cur.execute(
                    """
                    INSERT INTO shadow_runtime_execution_simulator (
                        symbol,
                        source,
                        readiness_status,
                        signal_source_table,
                        signals_seen,
                        virtual_entries,
                        virtual_exits,
                        virtual_pnl,
                        winrate,
                        expectancy,
                        simulator_status,
                        runtime_allowed,
                        execution_enabled,
                        raw_json
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,%s::jsonb)
                    """,
                    (
                        symbol,
                        row["source"],
                        row["readiness_status"],
                        source_table,
                        signals_seen,
                        virtual_entries,
                        virtual_exits,
                        virtual_pnl,
                        winrate,
                        expectancy,
                        status,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                print(
                    "SIMULATOR_ROW "
                    f"symbol={symbol} "
                    f"readiness={row['readiness_status']} "
                    f"source_table={source_table} "
                    f"signals_seen={signals_seen} "
                    f"virtual_entries={virtual_entries} "
                    f"virtual_exits={virtual_exits} "
                    f"simulator_status={status} "
                    "runtime_allowed=0 "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(
        "SUMMARY_ROW "
        f"active={active} "
        f"stale={stale} "
        f"blocked={blocked} "
        f"no_signals={no_signals}"
    )
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_EXECUTION_SIMULATOR_READY")
    print("SHADOW_RUNTIME_EXECUTION_SIMULATOR_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
