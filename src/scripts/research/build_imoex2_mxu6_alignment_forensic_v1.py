#!/usr/bin/env python3
"""
IMOEX2_MXU6_ALIGNMENT_FORENSIC_V1

Read-only forensic-анализ timestamp alignment:

IMOEX2 strategy signal trades
        ↓
MXU6 actual M5 bars

Цель:
- объяснить все несовпавшие entry/exit timestamps;
- не рассчитывать экономический результат;
- не изменять runtime/execution.
"""

from __future__ import annotations

import collections
import os

import psycopg2
import psycopg2.extras

from scripts.build_strategy_execution_runner_v1 import (
    Bar,
    build_trades,
)


SIGNAL_SYMBOL = "IMOEX2"
EXECUTION_SYMBOL = "MXU6@RTSX"
TIMEFRAME = "M5"

RUN = {
    "strategy_code": "MOMENTUM_CONTINUATION_V2",
    "parameter_json": {
        "lookback": 20,
        "hold": 5,
        "threshold": 0.5,
        "commission": 0.0,
        "slippage": 0.0,
    },
}


def main() -> int:
    print("=== IMOEX2 MXU6 ALIGNMENT FORENSIC V1 ===")
    print("mode=research_read_only")
    print(f"signal_symbol={SIGNAL_SYMBOL}")
    print(f"execution_symbol={EXECUTION_SYMBOL}")
    print(f"timeframe={TIMEFRAME}")
    print("economic_verdict_allowed=0")
    print()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT min(ts) AS first_ts, max(ts) AS last_ts
                FROM public.market_bars
                WHERE symbol=%s
                  AND timeframe=%s
                """,
                (EXECUTION_SYMBOL, TIMEFRAME),
            )

            bounds = dict(cur.fetchone() or {})
            first_ts = bounds.get("first_ts")
            last_ts = bounds.get("last_ts")

            if first_ts is None or last_ts is None:
                print(
                    "VERDICT="
                    "IMOEX2_MXU6_ALIGNMENT_FORENSIC_NO_EXECUTION_RANGE"
                )
                return 3

            cur.execute(
                """
                SELECT ts,close
                FROM public.market_bars
                WHERE symbol=%s
                  AND timeframe=%s
                  AND ts BETWEEN %s AND %s
                  AND close IS NOT NULL
                ORDER BY ts
                """,
                (
                    SIGNAL_SYMBOL,
                    TIMEFRAME,
                    first_ts,
                    last_ts,
                ),
            )

            signal_bars = [
                Bar(row["ts"], float(row["close"]))
                for row in cur.fetchall()
            ]

            cur.execute(
                """
                SELECT ts
                FROM public.market_bars
                WHERE symbol=%s
                  AND timeframe=%s
                  AND ts BETWEEN %s AND %s
                ORDER BY ts
                """,
                (
                    EXECUTION_SYMBOL,
                    TIMEFRAME,
                    first_ts,
                    last_ts,
                ),
            )

            execution_ts = {
                row["ts"]
                for row in cur.fetchall()
            }

        trades = build_trades(
            RUN,
            signal_bars,
        )

        counters = collections.Counter()
        missing_by_date = collections.Counter()
        missing_by_hour = collections.Counter()

        examples = []

        for trade in trades:
            entry_ts = trade.entry_ts
            exit_ts = trade.exit_ts

            entry_ok = entry_ts in execution_ts
            exit_ok = exit_ts in execution_ts

            if entry_ok and exit_ok:
                reason = "FULL_ALIGNMENT"
            elif not entry_ok and exit_ok:
                reason = "MISSING_ENTRY_BAR"
            elif entry_ok and not exit_ok:
                reason = "MISSING_EXIT_BAR"
            else:
                reason = "MISSING_ENTRY_AND_EXIT"

            counters[reason] += 1

            if reason != "FULL_ALIGNMENT":
                missing_by_date[entry_ts.date()] += 1
                missing_by_hour[entry_ts.hour] += 1

                if len(examples) < 25:
                    examples.append(
                        (
                            trade.no,
                            entry_ts,
                            exit_ts,
                            trade.side,
                            reason,
                        )
                    )

        total = len(trades)
        aligned = counters["FULL_ALIGNMENT"]
        missing = total - aligned

        ratio = (
            aligned / total
            if total
            else 0.0
        )

        print(
            "SUMMARY_ROW "
            f"trades={total} "
            f"aligned={aligned} "
            f"missing={missing} "
            f"alignment_ratio={ratio:.6f}"
        )

        print()
        print("REASON_ROWS")

        for reason in (
            "FULL_ALIGNMENT",
            "MISSING_ENTRY_BAR",
            "MISSING_EXIT_BAR",
            "MISSING_ENTRY_AND_EXIT",
        ):
            print(
                "REASON_ROW "
                f"reason={reason} "
                f"trades={counters[reason]}"
            )

        print()
        print("MISSING_DATE_ROWS")

        for date_value, count in sorted(
            missing_by_date.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        )[:30]:
            print(
                "MISSING_DATE_ROW "
                f"date={date_value} "
                f"trades={count}"
            )

        print()
        print("MISSING_HOUR_ROWS")

        for hour, count in sorted(
            missing_by_hour.items(),
        ):
            print(
                "MISSING_HOUR_ROW "
                f"hour_utc={hour} "
                f"trades={count}"
            )

        print()
        print("MISSING_EXAMPLES")

        for no, entry_ts, exit_ts, side, reason in examples:
            print(
                "MISSING_EXAMPLE "
                f"trade_no={no} "
                f"entry_ts={entry_ts} "
                f"exit_ts={exit_ts} "
                f"side={side} "
                f"reason={reason}"
            )

        print()
        print("economic_verdict_allowed=0")
        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if ratio >= 0.90:
            verdict = (
                "IMOEX2_MXU6_ALIGNMENT_FORENSIC_"
                "DIRECT_REPLAY_READY"
            )
        else:
            verdict = (
                "IMOEX2_MXU6_ALIGNMENT_FORENSIC_"
                "CALENDAR_MAPPING_REQUIRED"
            )

        print(f"VERDICT={verdict}")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
