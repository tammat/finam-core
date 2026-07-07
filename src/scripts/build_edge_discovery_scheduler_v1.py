from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

from marketcore.config import EdgeConfigProvider

SOURCE_VERSION = "EDGE_DISCOVERY_SCHEDULER_V1"
OUT_JSON = Path("reports/edge_discovery_scheduler_latest.json")


def json_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(type(obj).__name__)


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    cfg = EdgeConfigProvider().load()
    queued_count = 0
    skipped_count = 0
    reason = "OK"

    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT count(*) AS unsafe_rows
                FROM analytics.edge_candidate_v1
                WHERE micro_live_allowed=true OR live_allowed=true;
            """)
            unsafe_rows = int(cur.fetchone()["unsafe_rows"])

            cur.execute("""
                SELECT count(*) AS active_jobs
                FROM analytics.edge_discovery_queue_v1
                WHERE status IN ('NEW','RUNNING');
            """)
            active_jobs = int(cur.fetchone()["active_jobs"])

            cur.execute("""
                SELECT count(*) AS today_new
                FROM analytics.edge_discovery_queue_v1
                WHERE created_at::date = now()::date
                  AND event_code='RUN_RESEARCH';
            """)
            today_new = int(cur.fetchone()["today_new"])

            cur.execute("""
                SELECT
                    pipeline_stage,
                    recommendation_code,
                    expected_gain_pct,
                    severity
                FROM analytics.edge_factory_bottleneck_v1
                ORDER BY snapshot_ts DESC
                LIMIT 1;
            """)
            bottleneck = dict(cur.fetchone() or {})

            can_queue = (
                cfg.discovery_enabled()
                and cfg.auto_queue()
                and unsafe_rows == 0
                and active_jobs < cfg.max_parallel_research_jobs()
                and today_new < cfg.max_new_parameter_searches_per_day()
                and bottleneck.get("recommendation_code")
                and bottleneck.get("recommendation_code") != "NO_ACTION"
            )

            if can_queue:
                cur.execute("""
                    INSERT INTO analytics.edge_discovery_queue_v1 (
                        event_code,
                        priority,
                        status,
                        expected_edge_gain,
                        payload,
                        source_version
                    )
                    VALUES (%s,%s,%s,%s,%s,%s)
                    RETURNING id;
                """, (
                    "RUN_RESEARCH",
                    "HIGH" if Decimal(str(bottleneck.get("expected_gain_pct") or 0)) >= Decimal("15") else "NORMAL",
                    "NEW",
                    Decimal(str(bottleneck.get("expected_gain_pct") or 0)),
                    json.dumps({
                        "source": "EDGE_DISCOVERY_SCHEDULER_V1",
                        "recommendation_code": bottleneck.get("recommendation_code"),
                        "pipeline_stage": bottleneck.get("pipeline_stage"),
                        "severity": bottleneck.get("severity"),
                        "profile": cfg.profile(),
                        "max_trials": 100,
                    }, ensure_ascii=False),
                    SOURCE_VERSION,
                ))
                queue_id = int(cur.fetchone()["id"])
                queued_count = 1
                reason = f"QUEUED queue_id={queue_id}"
            else:
                skipped_count = 1
                if unsafe_rows != 0:
                    reason = "UNSAFE_ROWS_FOUND"
                elif not cfg.discovery_enabled():
                    reason = "DISCOVERY_DISABLED"
                elif not cfg.auto_queue():
                    reason = "AUTO_QUEUE_DISABLED"
                elif active_jobs >= cfg.max_parallel_research_jobs():
                    reason = "MAX_PARALLEL_RESEARCH_JOBS_REACHED"
                elif today_new >= cfg.max_new_parameter_searches_per_day():
                    reason = "MAX_NEW_PARAMETER_SEARCHES_PER_DAY_REACHED"
                else:
                    reason = "NO_ACTIONABLE_BOTTLENECK"

            cur.execute("""
                INSERT INTO analytics.edge_discovery_scheduler_v1 (
                    profile,
                    interval_minutes,
                    queued_count,
                    skipped_count,
                    status,
                    reason,
                    source_version
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s);
            """, (
                cfg.profile(),
                cfg.interval_minutes(),
                queued_count,
                skipped_count,
                "ACTIVE" if unsafe_rows == 0 else "BLOCKED",
                reason,
                SOURCE_VERSION,
            ))

    payload = {
        "source_version": SOURCE_VERSION,
        "generated_at": datetime.now(UTC),
        "profile": cfg.profile(),
        "interval_minutes": cfg.interval_minutes(),
        "queued_count": queued_count,
        "skipped_count": skipped_count,
        "reason": reason,
        "unsafe_rows": unsafe_rows,
        "verdict": "EDGE_DISCOVERY_SCHEDULER_READY" if unsafe_rows == 0 else "UNSAFE_ROWS_FOUND",
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")

    print("=== EDGE_DISCOVERY_SCHEDULER_V1 ===")
    print(f"profile={payload['profile']}")
    print(f"queued_count={queued_count}")
    print(f"skipped_count={skipped_count}")
    print(f"reason={reason}")
    print(f"unsafe_rows={unsafe_rows}")
    print(f"VERDICT={payload['verdict']}")


if __name__ == "__main__":
    main()
