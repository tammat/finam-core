from __future__ import annotations

import json
import runpy
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

from marketcore.config import EdgeConfigProvider

SOURCE_VERSION = "EDGE_DISCOVERY_AUTORUN_TIMER_V1"
OUT_JSON = Path("reports/edge_discovery_autorun_latest.json")


def json_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(type(obj).__name__)


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    cfg = EdgeConfigProvider().load()

    scheduler_runs = 0
    worker_runs = 0
    status = "STARTED"
    reason = "OK"
    unsafe_rows = 0

    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT count(*) AS unsafe_rows
                FROM analytics.edge_candidate_v1
                WHERE micro_live_allowed=true OR live_allowed=true;
            """)
            unsafe_rows = int(cur.fetchone()["unsafe_rows"])

            cur.execute("""
                SELECT max(started_at) AS last_started_at
                FROM analytics.edge_discovery_autorun_history_v1
                WHERE source_version=%s
                  AND status='FINISHED';
            """, (SOURCE_VERSION,))
            row = cur.fetchone()
            last_started_at = row["last_started_at"] if row else None

            should_run = True
            if last_started_at is not None:
                cur.execute("""
                    SELECT extract(epoch FROM (now() - %s)) / 60.0 AS minutes_since_last;
                """, (last_started_at,))
                minutes_since_last = Decimal(str(cur.fetchone()["minutes_since_last"] or 0))
                should_run = minutes_since_last >= Decimal(str(cfg.interval_minutes()))

            if unsafe_rows != 0:
                status = "BLOCKED"
                reason = "UNSAFE_ROWS_FOUND"
            elif not cfg.discovery_enabled():
                status = "BLOCKED"
                reason = "DISCOVERY_DISABLED"
            elif not should_run:
                status = "IDLE"
                reason = "INTERVAL_NOT_REACHED"
            else:
                status = "RUNNING"

    if status == "RUNNING":
        runpy.run_path("src/scripts/build_edge_discovery_scheduler_v1.py", run_name="__main__")
        scheduler_runs = 1

        runpy.run_path("src/scripts/build_edge_discovery_worker_v1.py", run_name="__main__")
        worker_runs = 1

        status = "FINISHED"
        reason = "SCHEDULER_AND_WORKER_DONE"

    duration = Decimal(str(round(time.monotonic() - started, 3)))

    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO analytics.edge_discovery_autorun_history_v1 (
                    finished_at,
                    duration_seconds,
                    scheduler_runs,
                    worker_runs,
                    status,
                    reason,
                    unsafe_rows,
                    source_version
                )
                VALUES (now(),%s,%s,%s,%s,%s,%s,%s);
            """, (
                duration,
                scheduler_runs,
                worker_runs,
                status,
                reason,
                unsafe_rows,
                SOURCE_VERSION,
            ))

    payload = {
        "source_version": SOURCE_VERSION,
        "generated_at": datetime.now(UTC),
        "profile": cfg.profile(),
        "interval_minutes": cfg.interval_minutes(),
        "scheduler_runs": scheduler_runs,
        "worker_runs": worker_runs,
        "status": status,
        "reason": reason,
        "unsafe_rows": unsafe_rows,
        "duration_seconds": duration,
        "verdict": "EDGE_DISCOVERY_AUTORUN_READY" if unsafe_rows == 0 else "UNSAFE_ROWS_FOUND",
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")

    print("=== EDGE_DISCOVERY_AUTORUN_TIMER_V1 ===")
    print(f"profile={payload['profile']}")
    print(f"interval_minutes={payload['interval_minutes']}")
    print(f"scheduler_runs={scheduler_runs}")
    print(f"worker_runs={worker_runs}")
    print(f"status={status}")
    print(f"reason={reason}")
    print(f"unsafe_rows={unsafe_rows}")
    print(f"VERDICT={payload['verdict']}")


if __name__ == "__main__":
    main()
