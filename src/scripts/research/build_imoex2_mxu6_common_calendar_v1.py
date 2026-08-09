#!/usr/bin/env python3

from __future__ import annotations

import os

import psycopg2
import psycopg2.extras


SIGNAL_SYMBOL = "IMOEX2"
EXECUTION_SYMBOL = "MXU6@RTSX"
TIMEFRAME = "M5"


def main() -> int:
    print("=== IMOEX2 MXU6 COMMON CALENDAR V1 ===")
    print("mode=research_read_only")
    print(f"signal_symbol={SIGNAL_SYMBOL}")
    print(f"execution_symbol={EXECUTION_SYMBOL}")
    print(f"timeframe={TIMEFRAME}")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(
                """
                WITH s AS (
                    SELECT ts
                    FROM public.market_bars
                    WHERE symbol=%s
                      AND timeframe=%s
                ),
                e AS (
                    SELECT ts
                    FROM public.market_bars
                    WHERE symbol=%s
                      AND timeframe=%s
                )
                SELECT
                    count(*) FILTER (
                        WHERE s.ts IS NOT NULL
                    ) AS signal_bars,
                    count(*) FILTER (
                        WHERE e.ts IS NOT NULL
                    ) AS execution_bars,
                    count(*) FILTER (
                        WHERE s.ts IS NOT NULL
                          AND e.ts IS NOT NULL
                    ) AS common_bars
                FROM s
                FULL OUTER JOIN e
                  ON e.ts=s.ts
                """,
                (
                    SIGNAL_SYMBOL,
                    TIMEFRAME,
                    EXECUTION_SYMBOL,
                    TIMEFRAME,
                ),
            )

            summary = dict(cur.fetchone() or {})

            cur.execute(
                """
                WITH common AS (
                    SELECT s.ts
                    FROM public.market_bars s
                    JOIN public.market_bars e
                      ON e.ts=s.ts
                     AND e.timeframe=s.timeframe
                    WHERE s.symbol=%s
                      AND e.symbol=%s
                      AND s.timeframe=%s
                )
                SELECT
                    ts::date AS trade_date,
                    count(*) AS common_bars,
                    min(ts) AS first_ts,
                    max(ts) AS last_ts
                FROM common
                GROUP BY ts::date
                ORDER BY trade_date
                """,
                (
                    SIGNAL_SYMBOL,
                    EXECUTION_SYMBOL,
                    TIMEFRAME,
                ),
            )

            days = [
                dict(row)
                for row in cur.fetchall()
            ]

        signal_bars = int(summary.get("signal_bars") or 0)
        execution_bars = int(summary.get("execution_bars") or 0)
        common_bars = int(summary.get("common_bars") or 0)

        common_ratio_signal = (
            common_bars / signal_bars
            if signal_bars
            else 0.0
        )

        common_ratio_execution = (
            common_bars / execution_bars
            if execution_bars
            else 0.0
        )

        print(
            "SUMMARY_ROW "
            f"signal_bars={signal_bars} "
            f"execution_bars={execution_bars} "
            f"common_bars={common_bars} "
            f"common_ratio_signal={common_ratio_signal:.6f} "
            f"common_ratio_execution={common_ratio_execution:.6f}"
        )

        print()
        print("COMMON_DAY_ROWS")

        for row in days[:40]:
            print(
                "COMMON_DAY_ROW "
                f"date={row['trade_date']} "
                f"bars={row['common_bars']} "
                f"first_ts={row['first_ts']} "
                f"last_ts={row['last_ts']}"
            )

        print()
        print("economic_verdict_allowed=0")
        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if common_bars > 0:
            print(
                "VERDICT="
                "IMOEX2_MXU6_COMMON_CALENDAR_READY"
            )
        else:
            print(
                "VERDICT="
                "IMOEX2_MXU6_COMMON_CALENDAR_EMPTY"
            )

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
