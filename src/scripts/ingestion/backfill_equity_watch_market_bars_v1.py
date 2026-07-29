#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys

import psycopg

FALLBACK_SYMBOLS = "GAZP@MISX,PLZL@MISX,SBER@MISX,LKOH@MISX"
LOOKBACK_HOURS = 24


def active_targets() -> dict[str, str]:
    database_url = os.environ.get("DATABASE_URL", "postgresql:///finam_core")
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT upper(coalesce(nullif(timeframe, ''), 'M5')) AS timeframe,
                       string_agg(symbol, ',' ORDER BY symbol)
                FROM runtime_active_universe
                WHERE is_enabled
                GROUP BY 1
                ORDER BY 1
            """)
            rows = cur.fetchall()
    return {timeframe: symbols for timeframe, symbols in rows} or {
        "M5": FALLBACK_SYMBOLS
    }

def main() -> int:
    ok_all = True
    targets = active_targets()
    print(f"EQUITY_MARKET_BARS_ACTIVE_TARGETS targets={targets}", flush=True)

    for tf, symbols in targets.items():
        cmd = [
            sys.executable,
            "src/scripts/ingestion/backfill_finam_futures_market_bars.py",
            "--symbols", symbols,
            "--timeframe", tf,
            "--lookback-hours", str(LOOKBACK_HOURS),
        ]

        print("EQUITY_MARKET_BARS_STEP_START", " ".join(cmd), flush=True)
        result = subprocess.run(cmd, check=False)
        ok = result.returncode == 0
        ok_all = ok_all and ok
        print(f"EQUITY_MARKET_BARS_STEP_DONE timeframe={tf} ok={ok} code={result.returncode}", flush=True)

    print(f"EQUITY_MARKET_BARS_SUMMARY ok={ok_all}", flush=True)
    return 0 if ok_all else 1

if __name__ == "__main__":
    raise SystemExit(main())
