from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

from marketcore.config import EdgeConfigProvider

SOURCE_VERSION = "EDGE_DISCOVERY_LOOP_V1"
OUT_JSON = Path("reports/edge_discovery_loop_latest.json")

def json_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")



def q(cur, sql: str) -> Decimal:
    cur.execute(sql)
    row = cur.fetchone()
    return Decimal(str(list(row.values())[0] or 0)) if row else Decimal("0")


def priority_from_gain(gain: Decimal) -> str:
    if gain >= Decimal("15"):
        return "HIGH"
    if gain >= Decimal("5"):
        return "NORMAL"
    return "LOW"


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    cfg = EdgeConfigProvider().load()

    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            unsafe = q(cur, """
                SELECT count(*)
                FROM analytics.edge_candidate_v1
                WHERE micro_live_allowed=true OR live_allowed=true
            """)

            today_new = q(cur, """
                SELECT count(*)
                FROM analytics.edge_discovery_queue_v1
                WHERE created_at::date = now()::date
                  AND event_code='RUN_RESEARCH'
            """)

            active_jobs = q(cur, """
                SELECT count(*)
                FROM analytics.edge_discovery_queue_v1
                WHERE status IN ('NEW','RUNNING')
            """)

            cur.execute("""
                SELECT pipeline_stage, recommendation_code, expected_gain_pct, severity
                FROM analytics.edge_factory_bottleneck_v1
                ORDER BY snapshot_ts DESC
                LIMIT 1
            """)
            bottleneck = dict(cur.fetchone() or {})

            event_code = "RUN_RESEARCH"
            recommendation = bottleneck.get("recommendation_code") or "NO_ACTION"
            expected_gain = Decimal(str(bottleneck.get("expected_gain_pct") or 0))

            allowed = (
                cfg.discovery_enabled()
                and cfg.auto_queue()
                and unsafe == 0
                and active_jobs < cfg.max_parallel_research_jobs()
                and today_new < cfg.max_new_parameter_searches_per_day()
                and recommendation != "NO_ACTION"
            )

            queued_id = None

            if allowed:
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
                    RETURNING id
                """, (
                    event_code,
                    priority_from_gain(expected_gain),
                    "NEW",
                    expected_gain,
                    json.dumps({
                        "recommendation_code": recommendation,
                        "pipeline_stage": bottleneck.get("pipeline_stage"),
                        "severity": bottleneck.get("severity"),
                        "profile": cfg.profile(),
                    }, ensure_ascii=False),
                    SOURCE_VERSION,
                ))
                queued_id = int(cur.fetchone()["id"])

                cur.execute("""
                    INSERT INTO analytics.edge_discovery_history_v1 (
                        queue_id,
                        event_code,
                        result_status,
                        result_json,
                        source_version
                    )
                    VALUES (%s,%s,%s,%s,%s)
                """, (
                    queued_id,
                    event_code,
                    "QUEUED",
                    json.dumps({"reason": "bottleneck_recommendation"}, ensure_ascii=False),
                    SOURCE_VERSION,
                ))

            payload = {
                "source_version": SOURCE_VERSION,
                "discovery_enabled": cfg.discovery_enabled(),
                "profile": cfg.profile(),
                "auto_queue": cfg.auto_queue(),
                "max_parallel_research_jobs": cfg.max_parallel_research_jobs(),
                "max_new_parameter_searches_per_day": cfg.max_new_parameter_searches_per_day(),
                "active_jobs": int(active_jobs),
                "today_new_research_jobs": int(today_new),
                "unsafe_rows": int(unsafe),
                "bottleneck": bottleneck,
                "queued": allowed,
                "queued_id": queued_id,
                "verdict": "EDGE_DISCOVERY_LOOP_READY" if unsafe == 0 else "UNSAFE_ROWS_FOUND",
            }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")

    print("=== EDGE_DISCOVERY_LOOP_V1 ===")
    print(f"profile={payload['profile']}")
    print(f"queued={int(payload['queued'])}")
    print(f"queued_id={payload['queued_id']}")
    print(f"active_jobs={payload['active_jobs']}")
    print(f"today_new_research_jobs={payload['today_new_research_jobs']}")
    print(f"unsafe_rows={payload['unsafe_rows']}")
    print(f"VERDICT={payload['verdict']}")


if __name__ == "__main__":
    main()
