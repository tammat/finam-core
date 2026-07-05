from __future__ import annotations

import json
import os
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

DEFAULT_SYMBOLS = ["BR@RTSX", "NG@RTSX", "LKOH@MISX", "SBER@MISX"]
MAX_STRATEGIES = int(os.getenv("RESEARCH_QUEUE_MAX_STRATEGIES", "10"))


def main() -> None:
    inserted = 0

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    strategy_code,
                    default_timeframes,
                    default_symbols,
                    priority
                FROM analytics.strategy_library_v1
                WHERE enabled=true
                ORDER BY priority ASC
                LIMIT %s;
            """, (MAX_STRATEGIES,))
            strategies = cur.fetchall()

            for s in strategies:
                symbols = list(s["default_symbols"] or []) or DEFAULT_SYMBOLS
                timeframes = list(s["default_timeframes"] or ["M5"])

                for symbol in symbols:
                    for timeframe in timeframes:
                        research_code = f"{s['strategy_code']}:{symbol}:{timeframe}:DEFAULT"
                        parameter_set = {}

                        cur.execute("""
                            INSERT INTO analytics.research_queue_v1 (
                                research_code,
                                strategy_code,
                                symbol,
                                timeframe,
                                parameter_set,
                                priority,
                                status_code,
                                source_version,
                                updated_at
                            )
                            VALUES (
                                %s,%s,%s,%s,%s::jsonb,%s,
                                'QUEUED',
                                'RESEARCH_QUEUE_V1',
                                now()
                            )
                            ON CONFLICT(strategy_code, symbol, timeframe, parameter_set)
                            DO UPDATE SET
                                research_code=EXCLUDED.research_code,
                                priority=EXCLUDED.priority,
                                source_version='RESEARCH_QUEUE_V1',
                                updated_at=now();
                        """, (
                            research_code,
                            s["strategy_code"],
                            symbol,
                            timeframe,
                            json.dumps(parameter_set),
                            s["priority"],
                        ))
                        inserted += 1

            cur.execute("""
                SELECT
                    count(*) AS total,
                    count(*) FILTER (WHERE status_code='QUEUED') AS queued,
                    count(*) FILTER (WHERE status_code='RUNNING') AS running,
                    count(*) FILTER (WHERE status_code='DONE') AS done,
                    count(*) FILTER (WHERE status_code='FAILED') AS failed
                FROM analytics.research_queue_v1;
            """)
            row = cur.fetchone()

    print("=== RESEARCH_QUEUE_V1 ===")
    print(f"queue_generated={inserted}")
    print(f"queue_total={row['total']}")
    print(f"queued={row['queued']}")
    print(f"running={row['running']}")
    print(f"done={row['done']}")
    print(f"failed={row['failed']}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=RESEARCH_QUEUE_V1_READY")


if __name__ == "__main__":
    main()
