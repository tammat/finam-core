from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

from marketcore.config import EdgeConfigProvider

SOURCE_VERSION = "EDGE_DISCOVERY_WORKER_V1"
OUT_JSON = Path("reports/edge_discovery_worker_latest.json")


def json_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(type(obj).__name__)


def run_research(cur, queue_id: int, payload: dict) -> dict:
    search_code = f"EDGE_LOOP_{queue_id}"
    cur.execute("""
        INSERT INTO analytics.parameter_search_job_v1 (
            search_code,
            strategy_code,
            symbol,
            timeframe,
            method_code,
            status_code,
            max_trials,
            objective_metric,
            source_version,
            updated_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
        ON CONFLICT(search_code) DO UPDATE SET
            status_code='QUEUED',
            updated_at=now()
    """, (
        search_code,
        payload.get("strategy_code", "AUTO_DISCOVERY"),
        payload.get("symbol", "AUTO_UNIVERSE"),
        payload.get("timeframe", "AUTO"),
        "GRID",
        "QUEUED",
        int(payload.get("max_trials", 100)),
        "normalized_edge_score",
        SOURCE_VERSION,
    ))
    return {"created_search_code": search_code}


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    cfg = EdgeConfigProvider().load()
    worker_name = os.getenv("WORKER_NAME", "edge_discovery_worker_v1")
    worker_pid = os.getpid()

    processed = []
    errors = []

    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT count(*) AS unsafe_rows
                FROM analytics.edge_candidate_v1
                WHERE micro_live_allowed=true OR live_allowed=true
            """)
            unsafe_rows = int(cur.fetchone()["unsafe_rows"])

            if unsafe_rows != 0 or not cfg.discovery_enabled():
                verdict = "EDGE_DISCOVERY_WORKER_BLOCKED"
            else:
                cur.execute("""
                    SELECT id, event_code, payload
                    FROM analytics.edge_discovery_queue_v1
                    WHERE status='NEW'
                      AND planned_at <= now()
                    ORDER BY expected_edge_gain DESC, planned_at ASC
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                """, (cfg.max_parallel_research_jobs(),))

                for job in cur.fetchall():
                    queue_id = int(job["id"])
                    event_code = job["event_code"]
                    payload = dict(job["payload"] or {})
                    start = time.monotonic()

                    try:
                        cur.execute("""
                            UPDATE analytics.edge_discovery_queue_v1
                            SET status='RUNNING',
                                worker_name=%s,
                                worker_pid=%s,
                                started_at=now(),
                                error_message=NULL
                            WHERE id=%s
                        """, (worker_name, worker_pid, queue_id))

                        if event_code == "RUN_RESEARCH":
                            result = run_research(cur, queue_id, payload)
                        elif event_code in ("PAPER_REPRICE", "RUN_RECOMMENDATION"):
                            result = {"status": "QUEUED_PLACEHOLDER", "event_code": event_code}
                        else:
                            raise RuntimeError(f"UNKNOWN_EVENT_CODE={event_code}")

                        elapsed = Decimal(str(round(time.monotonic() - start, 3)))

                        cur.execute("""
                            UPDATE analytics.edge_discovery_queue_v1
                            SET status='DONE',
                                finished_at=now(),
                                execution_seconds=%s
                            WHERE id=%s
                        """, (elapsed, queue_id))

                        cur.execute("""
                            INSERT INTO analytics.edge_discovery_history_v1 (
                                queue_id, event_code, result_status, result_json, source_version
                            )
                            VALUES (%s,%s,%s,%s,%s)
                        """, (
                            queue_id,
                            event_code,
                            "DONE",
                            json.dumps(result, ensure_ascii=False, default=json_default),
                            SOURCE_VERSION,
                        ))

                        processed.append({"queue_id": queue_id, "event_code": event_code, "result": result})

                    except Exception as exc:
                        elapsed = Decimal(str(round(time.monotonic() - start, 3)))
                        msg = str(exc)[:1000]

                        cur.execute("""
                            UPDATE analytics.edge_discovery_queue_v1
                            SET status='ERROR',
                                finished_at=now(),
                                execution_seconds=%s,
                                error_message=%s
                            WHERE id=%s
                        """, (elapsed, msg, queue_id))

                        cur.execute("""
                            INSERT INTO analytics.edge_discovery_history_v1 (
                                queue_id, event_code, result_status, result_json, source_version
                            )
                            VALUES (%s,%s,%s,%s,%s)
                        """, (
                            queue_id,
                            event_code,
                            "ERROR",
                            json.dumps({"error": msg}, ensure_ascii=False),
                            SOURCE_VERSION,
                        ))

                        errors.append({"queue_id": queue_id, "event_code": event_code, "error": msg})

                verdict = "EDGE_DISCOVERY_WORKER_READY" if not errors else "EDGE_DISCOVERY_WORKER_WITH_ERRORS"

    result = {
        "source_version": SOURCE_VERSION,
        "generated_at": datetime.now(UTC),
        "processed": processed,
        "errors": errors,
        "unsafe_rows": unsafe_rows,
        "verdict": verdict,
    }

    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")

    print("=== EDGE_DISCOVERY_WORKER_V1 ===")
    print(f"processed={len(processed)}")
    print(f"errors={len(errors)}")
    print(f"unsafe_rows={unsafe_rows}")
    print(f"VERDICT={verdict}")


if __name__ == "__main__":
    main()
