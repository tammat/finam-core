from __future__ import annotations

import os
import subprocess
import sys
import time

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.analytics.symbol_strategy_resolver import SymbolStrategyResolver


def load_symbols_with_new_trades(database_url: str, last_seen_id: int) -> tuple[int, list[str]]:
    sql = """
    SELECT
        COALESCE(MAX(id), %s) AS max_id
    FROM trades
    """

    symbols_sql = """
    SELECT DISTINCT symbol
    FROM trades
    WHERE id > %s
      AND symbol IS NOT NULL
      AND symbol <> ''
      AND (
          payload->>'paper_only' = 'true'
          OR trade_source ILIKE '%%paper%%'
          OR origin ILIKE '%%paper%%'
      )
    ORDER BY symbol
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (last_seen_id,))
            max_id = int(cur.fetchone()[0] or last_seen_id)

            cur.execute(symbols_sql, (last_seen_id,))
            symbols = [str(row[0]) for row in cur.fetchall()]

    return max_id, symbols


def run_refresh(symbol: str, timeframe: str, commission: str) -> int:
    strategy = SymbolStrategyResolver(build_psycopg_url()).resolve(symbol)

    cmd = [
        "./scripts/analytics_refresh_all.sh",
        symbol,
        strategy,
        timeframe,
        commission,
    ]

    print(
        "ANALYTICS_SUPERVISOR_REFRESH_START "
        f"symbol={symbol} strategy={strategy} timeframe={timeframe}",
        flush=True,
    )

    completed = subprocess.run(cmd, check=False)

    if completed.returncode == 0:
        print(
            "ANALYTICS_SUPERVISOR_REFRESH_OK "
            f"symbol={symbol} strategy={strategy} timeframe={timeframe}",
            flush=True,
        )
    else:
        print(
            "ANALYTICS_SUPERVISOR_REFRESH_FAILED "
            f"symbol={symbol} strategy={strategy} timeframe={timeframe} "
            f"returncode={completed.returncode}",
            flush=True,
        )

    return int(completed.returncode)


def main() -> int:
    database_url = build_psycopg_url()

    poll_sec = int(os.getenv("ANALYTICS_SUPERVISOR_POLL_SEC", "60"))
    timeframe = os.getenv("ANALYTICS_SUPERVISOR_TIMEFRAME", "M5")
    commission = os.getenv("ANALYTICS_SUPERVISOR_COMMISSION", "0.0001")
    once = os.getenv("ANALYTICS_SUPERVISOR_ONCE", "0") == "1"

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(id), 0) FROM trades")
            last_seen_id = int(cur.fetchone()[0] or 0)

    print(
        "ANALYTICS_SUPERVISOR_START "
        f"last_seen_id={last_seen_id} "
        f"poll_sec={poll_sec} "
        f"timeframe={timeframe} "
        f"once={once}",
        flush=True,
    )

    while True:
        max_id, symbols = load_symbols_with_new_trades(
            database_url=database_url,
            last_seen_id=last_seen_id,
        )

        if symbols:
            print(
                "ANALYTICS_SUPERVISOR_NEW_TRADES "
                f"from_id={last_seen_id} to_id={max_id} symbols={','.join(symbols)}",
                flush=True,
            )

            for symbol in symbols:
                run_refresh(symbol=symbol, timeframe=timeframe, commission=commission)

            last_seen_id = max_id
        else:
            print(
                "ANALYTICS_SUPERVISOR_IDLE "
                f"last_seen_id={last_seen_id}",
                flush=True,
            )

        if once:
            break

        time.sleep(poll_sec)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
