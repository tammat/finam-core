from __future__ import annotations

import os
import subprocess
import sys

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def load_active_symbols(database_url: str) -> list[str]:
    sql = """
    SELECT DISTINCT symbol
    FROM runtime_active_universe
    WHERE is_enabled = TRUE
      AND symbol IS NOT NULL
      AND symbol <> ''
    ORDER BY symbol
    """

    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return [str(row[0]) for row in cur.fetchall()]
    except Exception:
        return ["BRM6@RTSX"]


def run(cmd: list[str]) -> int:
    print("PORTFOLIO_GOVERNANCE_REFRESH_CMD " + " ".join(cmd), flush=True)
    completed = subprocess.run(cmd, check=False)
    return int(completed.returncode)


def main() -> int:
    database_url = build_psycopg_url()
    timeframe = os.getenv("PORTFOLIO_GOVERNANCE_TIMEFRAME", "M5")

    symbols = load_active_symbols(database_url)

    print(
        "PORTFOLIO_GOVERNANCE_REFRESH_START "
        f"symbols={len(symbols)} timeframe={timeframe}",
        flush=True,
    )

    rc = run([
        sys.executable,
        "src/scripts/build_portfolio_heat.py",
        "--cash",
        "0",
        "--migrate",
        "--save",
    ])

    if rc != 0:
        print("PORTFOLIO_GOVERNANCE_REFRESH_FAILED step=heat", flush=True)
        return rc

    failed = 0

    for symbol in symbols:
        rc = run([
            sys.executable,
            "src/scripts/build_portfolio_governance_event.py",
            "--symbol",
            symbol,
            "--timeframe",
            timeframe,
            "--migrate",
            "--save",
        ])

        if rc != 0:
            failed += 1
            print(
                "PORTFOLIO_GOVERNANCE_REFRESH_SYMBOL_FAILED "
                f"symbol={symbol} rc={rc}",
                flush=True,
            )

    print(
        "PORTFOLIO_GOVERNANCE_REFRESH_OK "
        f"symbols={len(symbols)} failed={failed}",
        flush=True,
    )

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
