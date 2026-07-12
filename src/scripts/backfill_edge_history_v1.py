from __future__ import annotations

import os
import subprocess
from datetime import date
from pathlib import Path

import psycopg2


ROOT = Path(__file__).resolve().parents[2]
PYTHON = os.getenv("MARKETCORE_PYTHON", str(ROOT / ".venv/bin/python"))
MONTH_CODES = "FGHJKMNQUVXZ"
START = date(2023, 7, 1)


def next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def run_backfill(symbol: str, start: date, end: date) -> None:
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        [
            PYTHON,
            "src/scripts/ingestion/backfill_finam_futures_market_bars.py",
            "--symbols", symbol,
            "--timeframe", "M5",
            "--start-date", start.isoformat(),
            "--end-date", end.isoformat(),
            "--chunk-days", "7",
            "--sleep-sec", "0.8",
        ],
        cwd=ROOT, env=env, text=True, capture_output=True,
        timeout=1200, check=False,
    )
    print(result.stdout, end="")
    if result.returncode:
        raise RuntimeError(f"BACKFILL_FAILED symbol={symbol} stderr={result.stderr[-1200:]}")


def history_ready(symbol: str, start: date, end: date, minimum_days: int) -> bool:
    with psycopg2.connect(os.getenv("DATABASE_URL", "postgresql:///finam_core")) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(DISTINCT (ts AT TIME ZONE 'Europe/Moscow')::date)
                FROM public.market_bars
                WHERE symbol=%s AND timeframe='M5'
                  AND ts >= %s::date AND ts < %s::date
                """,
                (symbol, start, end),
            )
            return int(cur.fetchone()[0] or 0) >= minimum_days


def run_step(script: str, *args: str, timeout: int = 1800) -> None:
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        [PYTHON, script, *args], cwd=ROOT, env=env, text=True,
        capture_output=True, timeout=timeout, check=False,
    )
    print(result.stdout, end="")
    if result.returncode:
        raise RuntimeError(f"POST_BACKFILL_STEP_FAILED script={script} stderr={result.stderr[-1200:]}")


def main() -> None:
    end = date.today()
    if history_ready("USDRUBF@RTSX", START, end, 650):
        print("symbol=USDRUBF@RTSX status=SKIPPED_HISTORY_READY")
    else:
        run_backfill("USDRUBF@RTSX", START, end)
    cursor = START
    contracts = 0
    while cursor < end:
        contract = f"NG{MONTH_CODES[cursor.month - 1]}{cursor.year % 10}@RTSX"
        contract_end = min(next_month(cursor), end)
        if history_ready(contract, cursor, contract_end, 15):
            print(f"symbol={contract} status=SKIPPED_HISTORY_READY")
        else:
            run_backfill(contract, cursor, contract_end)
        contracts += 1
        cursor = next_month(cursor)
    run_step(
        "src/scripts/build_historical_regime_snapshots_v2.py",
        "--symbols", "NG_ROLLING@RTSX,USDRUBF@RTSX",
    )
    run_step("src/scripts/build_relationship_data_quality_gate_v1.py")
    print(f"ng_contracts={contracts}")
    print("VERDICT=EDGE_HISTORY_BACKFILL_V1_OK")


if __name__ == "__main__":
    main()
