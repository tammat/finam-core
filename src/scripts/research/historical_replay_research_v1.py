from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


@dataclass(frozen=True)
class ReplayResearchDay:
    trade_date: date
    bars: int
    symbols: int


def load_available_days(
    database_url: str,
    symbols: list[str],
    timeframe: str,
    date_from: date,
    date_to: date,
) -> list[ReplayResearchDay]:
    sql = """
    SELECT
        (ts AT TIME ZONE 'Europe/Moscow')::date AS trade_date,
        count(*)::int AS bars,
        count(distinct symbol)::int AS symbols
    FROM market_bars
    WHERE symbol = ANY(%s)
      AND timeframe = %s
      AND (ts AT TIME ZONE 'Europe/Moscow')::date BETWEEN %s AND %s
    GROUP BY 1
    ORDER BY 1
    """

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (symbols, timeframe, date_from, date_to))
            return [
                ReplayResearchDay(
                    trade_date=row["trade_date"],
                    bars=int(row["bars"] or 0),
                    symbols=int(row["symbols"] or 0),
                )
                for row in cur.fetchall()
            ]


def run_cmd(cmd: list[str], dry_run: bool) -> int:
    print("HISTORICAL_REPLAY_CMD " + " ".join(cmd), flush=True)
    if dry_run:
        return 0

    result = subprocess.run(cmd)
    return int(result.returncode)


def run_day(
    *,
    py: str,
    symbols: list[str],
    trade_source: str,
    trade_date: date,
    dry_run: bool,
) -> int:
    # Русский комментарий:
    # На v1 запускаем research analytics для даты через уже созданные builders.
    # Live/paper execution pipeline не трогаем.
    cmds = [
        [
            py,
            "src/scripts/analytics/build_intraday_pnl.py",
            "--date",
            trade_date.isoformat(),
            "--migrate",
            "--save",
        ],
        [
            py,
            "src/scripts/analytics/build_regime_snapshots_v2.py",
            "--date",
            trade_date.isoformat(),
            "--migrate",
            "--save",
        ],
        [
            py,
            "src/scripts/analytics/build_trade_context_envelopes.py",
            "--date",
            trade_date.isoformat(),
            "--migrate",
            "--save",
        ],
        [
            py,
            "src/scripts/analytics/build_regime_aware_edge_v1.py",
            "--date",
            trade_date.isoformat(),
            "--migrate",
            "--save",
        ],
        [
            py,
            "src/scripts/analytics/build_edge_validation_table.py",
            "--date",
            trade_date.isoformat(),
            "--migrate",
            "--save",
        ],
    ]

    rc = 0
    for cmd in cmds:
        step_rc = run_cmd(cmd, dry_run=dry_run)
        if step_rc != 0:
            rc = step_rc
            print(
                f"HISTORICAL_REPLAY_DAY_STEP_FAILED date={trade_date} rc={step_rc} cmd={' '.join(cmd)}",
                flush=True,
            )
            break

    if rc == 0:
        print(f"HISTORICAL_REPLAY_DAY_OK date={trade_date}", flush=True)

    return rc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--from-date", required=True)
    parser.add_argument("--to-date", required=True)
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]
    if not symbols:
        raise SystemExit("symbols required")

    date_from = date.fromisoformat(args.from_date)
    date_to = date.fromisoformat(args.to_date)
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()
    py = sys.executable

    days = load_available_days(
        database_url=database_url,
        symbols=symbols,
        timeframe=args.timeframe,
        date_from=date_from,
        date_to=date_to,
    )

    print(
        "HISTORICAL_REPLAY_RESEARCH_START "
        f"symbols={','.join(symbols)} timeframe={args.timeframe} "
        f"from={date_from} to={date_to} days={len(days)} dry_run={args.dry_run}",
        flush=True,
    )

    failed = 0
    processed = 0

    for day in days:
        print(
            f"HISTORICAL_REPLAY_DAY date={day.trade_date} bars={day.bars} symbols={day.symbols}",
            flush=True,
        )
        rc = run_day(
            py=py,
            symbols=symbols,
            trade_source=args.trade_source,
            trade_date=day.trade_date,
            dry_run=args.dry_run,
        )
        processed += 1
        if rc != 0:
            failed += 1

    print(
        f"HISTORICAL_REPLAY_RESEARCH_SUMMARY processed={processed} failed={failed}",
        flush=True,
    )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
