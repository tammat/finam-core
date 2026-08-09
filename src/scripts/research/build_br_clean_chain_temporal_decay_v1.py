#!/usr/bin/env python3
"""
BR_CLEAN_CHAIN_TEMPORAL_DECAY_V1

Forensic-анализ временной деградации BR.

Источник:
    public.closed_trade_chains_v3

Допускаются только:
    strategy = BR_CONSERVATIVE_BREAKOUT
    timeframe = M5
    quality_status = FULL

Модуль:
- read-only;
- не изменяет runtime/execution;
- не перестраивает цепочки;
- не использует LIVE/LEGACY_BAD_IDENTITY;
- не включает незакрытые позиции.
"""

from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
import psycopg2.extras


STRATEGY = "BR_CONSERVATIVE_BREAKOUT"
TIMEFRAME = "M5"
SYMBOLS = (
    "BRM6@RTSX",
    "BRN6@RTSX",
    "BRQ6@RTSX",
)


SQL = """
SELECT
    id,
    symbol,
    strategy,
    timeframe,
    quality_status,
    entry_ts,
    exit_ts,
    net_pnl::numeric AS net_pnl
FROM closed_trade_chains_v3
WHERE symbol = ANY(%s)
  AND strategy = %s
  AND timeframe = %s
  AND quality_status = 'FULL'
ORDER BY entry_ts, id
"""


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def metrics(rows: list[dict]) -> dict:
    trades = len(rows)

    pnl = [dec(r["net_pnl"]) for r in rows]

    net = sum(pnl, Decimal("0"))
    gross_profit = sum(
        (x for x in pnl if x > 0),
        Decimal("0"),
    )
    gross_loss = abs(
        sum(
            (x for x in pnl if x < 0),
            Decimal("0"),
        )
    )

    wins = sum(1 for x in pnl if x > 0)
    losses = sum(1 for x in pnl if x < 0)

    expectancy = (
        net / Decimal(trades)
        if trades
        else Decimal("0")
    )

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else None
    )

    win_rate = (
        Decimal(wins) / Decimal(trades)
        if trades
        else Decimal("0")
    )

    return {
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "net_pnl": net,
        "expectancy": expectancy,
        "profit_factor": profit_factor,
        "win_rate": win_rate,
    }


def fmt_decimal(value: Decimal | None, places: int = 6) -> str:
    if value is None:
        return "None"

    quantum = Decimal("1").scaleb(-places)
    return str(value.quantize(quantum))


def print_metrics(prefix: str, extra: str, rows: list[dict]) -> None:
    m = metrics(rows)

    print(
        f"{prefix} "
        f"{extra} "
        f"trades={m['trades']} "
        f"wins={m['wins']} "
        f"losses={m['losses']} "
        f"win_rate={fmt_decimal(m['win_rate'], 4)} "
        f"net_pnl={fmt_decimal(m['net_pnl'])} "
        f"expectancy={fmt_decimal(m['expectancy'])} "
        f"profit_factor={fmt_decimal(m['profit_factor'], 4)}"
    )


def chronological_buckets(rows: list[dict]) -> list[tuple[str, list[dict]]]:
    total = len(rows)

    if total == 0:
        return [
            ("EARLY", []),
            ("MIDDLE", []),
            ("RECENT", []),
        ]

    # Хронологические трети без оптимизации по результатам.
    first_cut = total // 3
    second_cut = (2 * total) // 3

    return [
        ("EARLY", rows[:first_cut]),
        ("MIDDLE", rows[first_cut:second_cut]),
        ("RECENT", rows[second_cut:]),
    ]


def decay_verdict(rows: list[dict]) -> tuple[str, str]:
    buckets = chronological_buckets(rows)

    early = metrics(buckets[0][1])
    middle = metrics(buckets[1][1])
    recent = metrics(buckets[2][1])

    if min(
        early["trades"],
        middle["trades"],
        recent["trades"],
    ) == 0:
        return (
            "INSUFFICIENT_TEMPORAL_SAMPLE",
            "one_or_more_temporal_buckets_empty",
        )

    early_e = early["expectancy"]
    middle_e = middle["expectancy"]
    recent_e = recent["expectancy"]

    # Не называем decay ситуацию, где edge не был положительным изначально.
    if early_e <= 0:
        return (
            "NO_CONFIRMED_INITIAL_EDGE",
            "early_bucket_expectancy_non_positive",
        )

    if recent_e < 0 and recent_e < middle_e < early_e:
        return (
            "MONOTONIC_DECAY_CONFIRMED",
            "expectancy_declines_early_middle_recent",
        )

    if recent_e < 0:
        return (
            "RECENT_DECAY_CONFIRMED",
            "early_positive_recent_negative",
        )

    if recent_e < early_e:
        return (
            "DECAY_WARNING",
            "recent_expectancy_below_early_but_positive",
        )

    return (
        "NO_TEMPORAL_DECAY_CONFIRMED",
        "recent_expectancy_not_weaker_than_early",
    )


def main() -> int:
    print("=== BR CLEAN CHAIN TEMPORAL DECAY V1 ===")
    print("mode=research_read_only")
    print("source=closed_trade_chains_v3")
    print("quality_status=FULL")
    print(f"strategy={STRATEGY}")
    print(f"timeframe={TIMEFRAME}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                SQL,
                (
                    list(SYMBOLS),
                    STRATEGY,
                    TIMEFRAME,
                ),
            )
            rows = [dict(r) for r in cur.fetchall()]

        print("CONTRACT_ROWS")

        for symbol in SYMBOLS:
            subset = [
                r for r in rows
                if r["symbol"] == symbol
            ]

            print_metrics(
                "CONTRACT_ROW",
                f"symbol={symbol}",
                subset,
            )

        print()
        print("DAILY_ROWS")

        days = sorted({
            r["entry_ts"].date()
            for r in rows
        })

        for day in days:
            subset = [
                r for r in rows
                if r["entry_ts"].date() == day
            ]

            print_metrics(
                "DAILY_ROW",
                f"day={day}",
                subset,
            )

        print()
        print("TEMPORAL_BUCKET_ROWS")

        for bucket, subset in chronological_buckets(rows):
            first_entry = (
                subset[0]["entry_ts"]
                if subset else None
            )
            last_exit = (
                max(r["exit_ts"] for r in subset)
                if subset else None
            )

            print_metrics(
                "TEMPORAL_BUCKET_ROW",
                (
                    f"bucket={bucket} "
                    f"first_entry={first_entry} "
                    f"last_exit={last_exit}"
                ),
                subset,
            )

        verdict, reason = decay_verdict(rows)

        print()
        print("SUMMARY_ROW")
        print_metrics(
            "BR_FULL_CHAIN_SUMMARY",
            "scope=ALL_BR_FULL_CHAINS",
            rows,
        )

        print(f"full_chains={len(rows)}")
        print(f"decay_status={verdict}")
        print(f"reason={reason}")
        print("db_writes_performed=0")
        print("runtime_allow=0")
        print("execution_enabled=0")
        print(f"VERDICT=BR_CLEAN_CHAIN_TEMPORAL_DECAY_V1_{verdict}")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
