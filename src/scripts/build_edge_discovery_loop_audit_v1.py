from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "EDGE_DISCOVERY_LOOP_AUDIT_V1"
OUT_JSON = Path("reports/edge_discovery_loop_audit_latest.json")


def json_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(type(obj).__name__)


def scalar(cur, sql: str) -> int:
    cur.execute(sql)
    row = cur.fetchone()
    if not row:
        return 0
    return int(list(row.values())[0] or 0)


def add(results: list[dict], name: str, ok: bool, details: dict) -> None:
    results.append({
        "check_name": name,
        "result": "PASS" if ok else "FAIL",
        "details": details,
    })


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    checks: list[dict] = []

    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            config_rows = scalar(cur, """
                SELECT count(*)
                FROM analytics.edge_configuration_v1
                WHERE edge_name='EDGE_DISCOVERY_LOOP'
                  AND enabled=true
                  AND config_json ? 'max_parallel_research_jobs'
                  AND config_json ? 'max_new_parameter_searches_per_day'
            """)
            add(checks, "CONFIG", config_rows == 1, {"config_rows": config_rows})

            scheduler_rows = scalar(cur, """
                SELECT count(*)
                FROM analytics.edge_discovery_scheduler_v1
                WHERE source_version='EDGE_DISCOVERY_SCHEDULER_V1'
            """)
            add(checks, "SCHEDULER", scheduler_rows > 0, {"scheduler_rows": scheduler_rows})

            queue_rows = scalar(cur, """
                SELECT count(*)
                FROM analytics.edge_discovery_queue_v1
            """)
            stuck_rows = scalar(cur, """
                SELECT count(*)
                FROM analytics.edge_discovery_queue_v1
                WHERE status='RUNNING'
                  AND started_at < now() - interval '30 minutes'
            """)
            add(checks, "QUEUE", queue_rows > 0 and stuck_rows == 0, {
                "queue_rows": queue_rows,
                "stuck_rows": stuck_rows,
            })

            worker_done_rows = scalar(cur, """
                SELECT count(*)
                FROM analytics.edge_discovery_history_v1
                WHERE source_version='EDGE_DISCOVERY_WORKER_V1'
                  AND result_status='DONE'
            """)
            worker_error_rows = scalar(cur, """
                SELECT count(*)
                FROM analytics.edge_discovery_history_v1
                WHERE source_version='EDGE_DISCOVERY_WORKER_V1'
                  AND result_status='ERROR'
            """)
            add(checks, "WORKER", worker_done_rows > 0 and worker_error_rows == 0, {
                "worker_done_rows": worker_done_rows,
                "worker_error_rows": worker_error_rows,
            })

            research_jobs = scalar(cur, """
                SELECT count(*)
                FROM analytics.parameter_search_job_v1
                WHERE source_version='EDGE_DISCOVERY_WORKER_V1'
            """)
            add(checks, "RESEARCH_JOB", research_jobs > 0, {"research_jobs": research_jobs})

            orphan_history = scalar(cur, """
                SELECT count(*)
                FROM analytics.edge_discovery_history_v1 h
                LEFT JOIN analytics.edge_discovery_queue_v1 q ON q.id=h.queue_id
                WHERE h.queue_id IS NOT NULL
                  AND q.id IS NULL
            """)
            add(checks, "HISTORY_LINKS", orphan_history == 0, {"orphan_history": orphan_history})

            autorun_rows = scalar(cur, """
                SELECT count(*)
                FROM analytics.edge_discovery_autorun_history_v1
                WHERE source_version='EDGE_DISCOVERY_AUTORUN_TIMER_V1'
            """)
            add(checks, "AUTORUN", autorun_rows > 0, {"autorun_rows": autorun_rows})

            unsafe_rows = scalar(cur, """
                SELECT count(*)
                FROM analytics.edge_candidate_v1
                WHERE micro_live_allowed=true OR live_allowed=true
            """)
            add(checks, "SAFETY", unsafe_rows == 0, {"unsafe_rows": unsafe_rows})

            labels = scalar(cur, """
                SELECT count(*)
                FROM presentation.ui_resource_v1
                WHERE resource_group='edge_discovery'
                  AND resource_key LIKE 'edge.discovery.audit.%'
                  AND locale_code='ru'
            """)
            add(checks, "I18N", labels >= 5, {"i18n_labels": labels})

            failed = [x for x in checks if x["result"] != "PASS"]
            overall = "PASS" if not failed else "FAIL"

            for row in checks:
                cur.execute("""
                    INSERT INTO analytics.edge_discovery_loop_audit_v1 (
                        audit_name,
                        check_name,
                        result,
                        details,
                        source_version
                    )
                    VALUES (%s,%s,%s,%s,%s)
                """, (
                    "EDGE_DISCOVERY_LOOP_AUDIT",
                    row["check_name"],
                    row["result"],
                    json.dumps(row["details"], ensure_ascii=False, default=json_default),
                    SOURCE_VERSION,
                ))

    payload = {
        "source_version": SOURCE_VERSION,
        "generated_at": datetime.now(UTC),
        "overall": overall,
        "checks": checks,
        "verdict": "EDGE_DISCOVERY_LOOP_AUDIT_READY" if overall == "PASS" else "EDGE_DISCOVERY_LOOP_AUDIT_FAILED",
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")

    print("=== EDGE_DISCOVERY_LOOP_AUDIT_V1 ===")
    for row in checks:
        print(f"CHECK {row['check_name']}={row['result']} details={row['details']}")
    print(f"OVERALL={overall}")
    print(f"VERDICT={payload['verdict']}")


if __name__ == "__main__":
    main()
