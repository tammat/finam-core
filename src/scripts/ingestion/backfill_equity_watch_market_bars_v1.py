#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys

SYMBOLS = "GAZP@MISX,PLZL@MISX,SBER@MISX,LKOH@MISX"
TIMEFRAMES = ["M1", "M5", "H1"]
LOOKBACK_HOURS = 24

def main() -> int:
    ok_all = True

    for tf in TIMEFRAMES:
        cmd = [
            sys.executable,
            "src/scripts/ingestion/backfill_finam_futures_market_bars.py",
            "--symbols", SYMBOLS,
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
