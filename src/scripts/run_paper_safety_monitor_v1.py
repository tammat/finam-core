from __future__ import annotations

import os
import time
import traceback

import psycopg2
import psycopg2.extras

from scripts.run_real_portfolio_position_sync import main as sync_broker_positions


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
WORKER_CODE = "PAPER_SAFETY_MONITOR_V1"


def record(status: str, *, positions: int = 0, breaches: int = 0, error: str | None = None) -> None:
    with psycopg2.connect(DB) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO analytics.paper_safety_monitor_v1(
                       worker_code,status_code,last_started_at,last_success_at,last_failure_at,
                       broker_positions,breaches,last_error,updated_at)
                   VALUES(%s,%s,clock_timestamp(),
                       CASE WHEN %s='HEALTHY' THEN clock_timestamp() END,
                       CASE WHEN %s='FAILED' THEN clock_timestamp() END,
                       %s,%s,%s,clock_timestamp())
                   ON CONFLICT(worker_code) DO UPDATE SET
                       status_code=excluded.status_code,last_started_at=excluded.last_started_at,
                       last_success_at=coalesce(excluded.last_success_at,analytics.paper_safety_monitor_v1.last_success_at),
                       last_failure_at=coalesce(excluded.last_failure_at,analytics.paper_safety_monitor_v1.last_failure_at),
                       broker_positions=excluded.broker_positions,breaches=excluded.breaches,
                       last_error=excluded.last_error,updated_at=clock_timestamp()""",
                (WORKER_CODE, status, status, status, positions, breaches, error),
            )


def inspect_positions() -> tuple[int, int]:
    max_qty = float(os.getenv("REAL_EXECUTION_MAX_QTY", "1"))
    allowlist = {
        item.strip().upper()
        for item in os.getenv("REAL_EXECUTION_SYMBOL_ALLOWLIST", "").split(",")
        if item.strip()
    }
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(
                """SELECT symbol,abs(qty)::float qty
                   FROM public.real_portfolio_positions
                   WHERE abs(qty)>0"""
            )
            rows = cursor.fetchall()
    breaches = sum(
        1 for row in rows
        if str(row["symbol"]).upper() in allowlist and float(row["qty"]) > max_qty
    )
    return len(rows), breaches


def sync_is_fresh() -> bool:
    max_age = max(30, int(os.getenv("BROKER_POSITION_SYNC_MAX_AGE_SEC", "180")))
    with psycopg2.connect(DB) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT status_code='HEALTHY'
                          AND last_success_at>=clock_timestamp()-(%s*interval '1 second')
                   FROM analytics.broker_position_sync_state_v1
                   WHERE worker_code='FINAM_POSITION_SYNC'""",
                (max_age,),
            )
            row = cursor.fetchone()
    return bool(row and row[0])


def cycle() -> None:
    record("RUNNING")
    sync_result = sync_broker_positions()
    if sync_result != 0 or not sync_is_fresh():
        raise RuntimeError(f"BROKER_POSITION_SYNC_NOT_FRESH:return_code={sync_result}")
    positions, breaches = inspect_positions()
    status = "ALERT" if breaches else "HEALTHY"
    record(status, positions=positions, breaches=breaches)
    print(
        f"PAPER_SAFETY_MONITOR status={status} broker_positions={positions} breaches={breaches}",
        flush=True,
    )


def main() -> int:
    interval = max(15, int(os.getenv("PAPER_SAFETY_MONITOR_INTERVAL_SEC", "60")))
    if os.getenv("REAL_EXECUTION_ENABLED", "0") == "1" or os.getenv("REAL_ORDER_CONFIRM", "0") == "1":
        raise RuntimeError("PAPER_SAFETY_MONITOR_REQUIRES_REAL_EXECUTION_DISABLED")
    print(f"PAPER_SAFETY_MONITOR_STARTED interval_sec={interval}", flush=True)
    while True:
        started = time.monotonic()
        try:
            cycle()
        except Exception as exc:
            detail = f"{type(exc).__name__}:{exc}"[:2000]
            try:
                record("FAILED", error=detail)
            except Exception:
                pass
            print(f"PAPER_SAFETY_MONITOR_FAILED error={detail}", flush=True)
            traceback.print_exc()
        time.sleep(max(1.0, interval - (time.monotonic() - started)))


if __name__ == "__main__":
    raise SystemExit(main())
