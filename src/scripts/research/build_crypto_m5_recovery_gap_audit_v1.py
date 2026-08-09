#!/usr/bin/env python3
"""
CRYPTO_M5_RECOVERY_GAP_AUDIT_V1

Read-only аудит BTCUSD/ETHUSD после crypto backfill.

Не делает backfill.
Не пишет в PostgreSQL.
Не меняет systemd/runtime.
"""

from __future__ import annotations

import os
import subprocess

import psycopg
from psycopg.rows import dict_row


SYMBOLS = ("BTCUSD", "ETHUSD")
TIMEFRAME = "M5"
UNIT = "finam-crypto-backfill.service"


def command(args: list[str]) -> str:
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    return (result.stdout or result.stderr or "").strip()


def main() -> int:
    print("=== CRYPTO M5 RECOVERY GAP AUDIT V1 ===")
    print("mode=research_read_only")
    print(f"timeframe={TIMEFRAME}")

    db = os.environ["DATABASE_URL"]

    with psycopg.connect(db, row_factory=dict_row) as conn:
        conn.execute("SET TRANSACTION READ ONLY")

        rows = conn.execute(
            """
            WITH latest AS (
                SELECT max(ts) AS universe_latest_ts
                FROM public.market_bars
                WHERE symbol IN ('BTCUSD','ETHUSD')
                  AND timeframe=%s
            )
            SELECT
                b.symbol,
                count(*) AS bars,
                max(b.ts) AS last_ts,
                l.universe_latest_ts,
                extract(
                    epoch FROM (
                        l.universe_latest_ts - max(b.ts)
                    )
                ) / 3600.0 AS relative_staleness_hours
            FROM public.market_bars b
            CROSS JOIN latest l
            WHERE b.symbol = ANY(%s)
              AND b.timeframe=%s
            GROUP BY b.symbol,l.universe_latest_ts
            ORDER BY b.symbol
            """,
            (TIMEFRAME, list(SYMBOLS), TIMEFRAME),
        ).fetchall()

    by_symbol = {
        row["symbol"]: row
        for row in rows
    }

    for symbol in SYMBOLS:
        row = by_symbol.get(symbol)

        if not row:
            print(
                "CRYPTO_ROW "
                f"symbol={symbol} "
                "status=MISSING_SERIES"
            )
            continue

        stale = float(
            row["relative_staleness_hours"] or 0
        )

        status = (
            "FRESH"
            if stale <= 1.0
            else "STALE"
        )

        print(
            "CRYPTO_ROW "
            f"symbol={symbol} "
            f"bars={row['bars']} "
            f"last_ts={row['last_ts']} "
            f"relative_staleness_hours={stale:.2f} "
            f"status={status}"
        )

    result = command(
        [
            "systemctl",
            "show",
            UNIT,
            "-p",
            "Result",
            "-p",
            "ExecMainStatus",
            "--no-pager",
        ]
    )

    print()
    print(
        "SERVICE_ROW "
        + " ".join(result.splitlines())
    )

    journal = command(
        [
            "journalctl",
            "-u",
            UNIT,
            "-n",
            "120",
            "--no-pager",
        ]
    )

    eth_mentions = [
        line.strip()
        for line in journal.splitlines()
        if "ETH" in line.upper()
    ]

    btc_mentions = [
        line.strip()
        for line in journal.splitlines()
        if "BTC" in line.upper()
    ]

    print(
        "JOURNAL_SUMMARY "
        f"btc_mentions={len(btc_mentions)} "
        f"eth_mentions={len(eth_mentions)}"
    )

    btc = by_symbol.get("BTCUSD")
    eth = by_symbol.get("ETHUSD")

    btc_fresh = (
        btc is not None
        and float(
            btc["relative_staleness_hours"] or 0
        ) <= 1.0
    )

    eth_fresh = (
        eth is not None
        and float(
            eth["relative_staleness_hours"] or 0
        ) <= 1.0
    )

    print()
    print(f"btc_fresh={int(btc_fresh)}")
    print(f"eth_fresh={int(eth_fresh)}")
    print("db_writes_performed=0")
    print("backfill_executed=0")
    print("systemd_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("micro_live_allowed=0")

    if btc_fresh and eth_fresh:
        verdict = "CRYPTO_M5_RECOVERY_COMPLETE"
    elif btc_fresh and not eth_fresh:
        verdict = "CRYPTO_M5_RECOVERY_PARTIAL_ETH_STALE"
    else:
        verdict = "CRYPTO_M5_RECOVERY_NOT_READY"

    print(f"VERDICT={verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
