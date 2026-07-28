from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path("/opt/finam-core")
PYTHON = ROOT / "venv/bin/python"
SCOPE = "SWING_EDGE_SEARCH"
LOCK_ID = 941903129


def market_hours(now: datetime) -> bool:
    local = now.astimezone(ZoneInfo("Europe/Moscow"))
    minute = local.hour * 60 + local.minute
    return (
        (local.weekday() < 5 and 7 * 60 <= minute < 23 * 60 + 50)
        or (local.weekday() == 6 and 10 * 60 <= minute < 19 * 60)
    )


def bars_advanced(previous: dict[str, str | None], current: dict[str, str | None]) -> bool:
    def parsed(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value) if value else None

    for timeframe in ("H1", "H4", "D1"):
        latest = parsed(current.get(timeframe))
        seen = parsed(previous.get(timeframe))
        if latest is not None and (seen is None or latest > seen):
            return True
    return False


def load_closed_bars(cursor) -> dict[str, str | None]:
    cursor.execute("""
        SELECT timeframe, max(ts) AS latest
        FROM analytics.swing_market_bars_v1
        WHERE (timeframe='H1' AND ts + interval '1 hour' <= clock_timestamp())
           OR (timeframe='H4' AND ts + interval '4 hours' <= clock_timestamp())
           OR (timeframe='D1' AND ts + interval '1 day' <= clock_timestamp())
        GROUP BY timeframe
    """)
    values = {"H1": None, "H4": None, "D1": None}
    for row in cursor.fetchall():
        values[row["timeframe"]] = row["latest"].isoformat() if row["latest"] else None
    return values


def write_state(cursor, status: str, reason: str, observed: dict, *, consume: bool = False) -> None:
    cursor.execute("""
        INSERT INTO analytics.swing_closed_bar_cycle_checkpoint_v1(
            scope_code,status_code,last_seen_bars,observed_bars,reason_code,
            load_1m,last_started_at,last_finished_at,heartbeat_at,updated_at)
        VALUES(%s,%s,CASE WHEN %s THEN %s::jsonb ELSE '{}'::jsonb END,%s::jsonb,%s,
               %s,CASE WHEN %s='RUNNING' THEN clock_timestamp() END,
               CASE WHEN %s IN ('COMPLETE','WAITING_NEW_BAR','DEFERRED_LOAD','FAILED') THEN clock_timestamp() END,
               clock_timestamp(),clock_timestamp())
        ON CONFLICT(scope_code) DO UPDATE SET
            status_code=excluded.status_code,
            last_seen_bars=CASE WHEN %s THEN excluded.observed_bars ELSE analytics.swing_closed_bar_cycle_checkpoint_v1.last_seen_bars END,
            observed_bars=excluded.observed_bars,reason_code=excluded.reason_code,
            load_1m=excluded.load_1m,
            last_started_at=CASE WHEN excluded.status_code='RUNNING' THEN clock_timestamp() ELSE analytics.swing_closed_bar_cycle_checkpoint_v1.last_started_at END,
            last_finished_at=CASE WHEN excluded.status_code IN ('COMPLETE','WAITING_NEW_BAR','DEFERRED_LOAD','FAILED') THEN clock_timestamp() ELSE analytics.swing_closed_bar_cycle_checkpoint_v1.last_finished_at END,
            heartbeat_at=clock_timestamp(),updated_at=clock_timestamp()
    """, (SCOPE, status, consume, json.dumps(observed), json.dumps(observed), reason,
          os.getloadavg()[0], status, status, consume))


def main() -> int:
    now = datetime.now(ZoneInfo("UTC"))
    connection = psycopg2.connect(DB)
    try:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s) AS locked", (LOCK_ID,))
            if not cursor.fetchone()["locked"]:
                print("VERDICT=SWING_CLOSED_BAR_SEARCH_ALREADY_RUNNING")
                return 0
            cursor.execute("""SELECT enabled,market_load_limit,offhours_load_limit
                FROM analytics.swing_closed_bar_schedule_policy_v1 WHERE policy_code=%s""", (SCOPE,))
            policy = cursor.fetchone()
            if not policy or not policy["enabled"]:
                print("VERDICT=SWING_CLOSED_BAR_SEARCH_DISABLED")
                return 0
            current = load_closed_bars(cursor)
            cursor.execute("SELECT last_seen_bars FROM analytics.swing_closed_bar_cycle_checkpoint_v1 WHERE scope_code=%s", (SCOPE,))
            row = cursor.fetchone()
            previous = dict(row["last_seen_bars"]) if row else {}
            if not bars_advanced(previous, current):
                write_state(cursor, "WAITING_NEW_BAR", "NO_NEW_CLOSED_H1_H4_D1_BAR", current)
                connection.commit()
                print("closed_bars=" + json.dumps(current, ensure_ascii=False))
                print("VERDICT=WAITING_NEW_CLOSED_SWING_BAR")
                return 0
            limit = float(policy["market_load_limit"] if market_hours(now) else policy["offhours_load_limit"])
            if os.getloadavg()[0] > limit:
                write_state(cursor, "DEFERRED_LOAD", "SERVER_LOAD_LIMIT", current)
                connection.commit()
                print(f"load_1m={os.getloadavg()[0]:.2f} limit={limit:.2f}")
                print("VERDICT=SWING_SEARCH_DEFERRED_BY_LOAD")
                return 0
            write_state(cursor, "RUNNING", "NEW_CLOSED_BAR_DETECTED", current)
            connection.commit()

        # Keep the session-level advisory lock for the whole child process.
        # Releasing it before subprocess completion allows a second scheduler
        # invocation to consume the same closed-bar checkpoint prematurely.
        result = subprocess.run(
            [str(PYTHON), "src/scripts/run_swing_edge_search_cycle_v1.py"],
            cwd=ROOT, env=os.environ.copy(), text=True, capture_output=True, check=False,
        )
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            if result.returncode == 0:
                write_state(cursor, "COMPLETE", "CLOSED_BAR_CYCLE_COMPLETE", current, consume=True)
            else:
                write_state(cursor, "FAILED", "EDGE_SEARCH_PROCESS_FAILED", current)
            connection.commit()
        print(result.stdout[-4000:])
        if result.stderr:
            print(result.stderr[-4000:])
        print("VERDICT=" + ("SWING_CLOSED_BAR_CYCLE_COMPLETE" if result.returncode == 0 else "SWING_CLOSED_BAR_CYCLE_FAILED"))
        return result.returncode
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
