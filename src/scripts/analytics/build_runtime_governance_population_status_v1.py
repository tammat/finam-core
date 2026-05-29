from __future__ import annotations

import argparse
import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SOURCE = "paper_pipeline_phase2_runtime"


SUMMARY_SQL = """
SELECT
    count(*) AS total_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    count(*) FILTER (WHERE action = 'ALLOW') AS allow_action_rows,
    count(*) FILTER (WHERE action = 'SOFT_BLOCK') AS soft_block_rows,
    count(*) FILTER (WHERE action = 'FAILED_OPEN') AS failed_open_rows,
    round(avg(expectancy_points)::numeric, 6) AS avg_expectancy_points,
    min(created_at) AS first_event_ts,
    max(created_at) AS last_event_ts,
    round(
        extract(
            epoch from (
                now() - max(created_at)
            )
        )::numeric / 3600,
        4
    ) AS hours_since_last_event
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour');
"""


SESSION_SQL = """
SELECT
    hour_msk,
    side,
    count(*) AS total_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    round(avg(expectancy_points)::numeric, 6) AS avg_expectancy_points,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour')
GROUP BY hour_msk, side
ORDER BY total_rows DESC, hour_msk, side
LIMIT 20;
"""


ACTION_SQL = """
SELECT
    action,
    reason,
    count(*) AS total_rows,
    round(avg(expectancy_points)::numeric, 6) AS avg_expectancy_points,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour')
GROUP BY action, reason
ORDER BY total_rows DESC, action, reason
LIMIT 20;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def sample_status(total_rows: int) -> str:
    if total_rows <= 0:
        return "EMPTY"
    if total_rows < 10:
        return "EARLY_SAMPLE"
    if total_rows < 30:
        return "BUILDING"
    if total_rows < 50:
        return "ANALYSIS_READY"
    if total_rows < 100:
        return "GOOD_SAMPLE"
    return "STRONG_SAMPLE"


def readiness_note(status: str) -> str:
    if status == "EMPTY":
        return "нет_реальных_phase2_событий"
    if status == "EARLY_SAMPLE":
        return "выборка_есть_но_слишком_мала"
    if status == "BUILDING":
        return "идет_накопление_до_минимума_30"
    if status == "ANALYSIS_READY":
        return "можно_делать_первичную_оценку"
    if status == "GOOD_SAMPLE":
        return "можно_делать_устойчивую_оценку"
    return "можно_делать_сильную_статистическую_оценку"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-hours", type=int, default=24 * 7)
    args = parser.parse_args()

    params = {
        "source": SOURCE,
        "window_hours": args.window_hours,
    }

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SUMMARY_SQL, params)
            summary = dict(cur.fetchone())

            cur.execute(SESSION_SQL, params)
            session_rows = [dict(row) for row in cur.fetchall()]

            cur.execute(ACTION_SQL, params)
            action_rows = [dict(row) for row in cur.fetchall()]

    total_rows = int(summary["total_rows"] or 0)
    status = sample_status(total_rows)

    print("RUNTIME_GOVERNANCE_POPULATION_STATUS_V1")
    print(
        "RUNTIME_GOVERNANCE_POPULATION_SUMMARY",
        f"status={status}",
        f"note={readiness_note(status)}",
        f"git_clean={git_clean()}",
        f"source={SOURCE}",
        f"window_hours={args.window_hours}",
        f"total_rows={summary['total_rows']}",
        f"allowed_rows={summary['allowed_rows']}",
        f"blocked_rows={summary['blocked_rows']}",
        f"allow_action_rows={summary['allow_action_rows']}",
        f"soft_block_rows={summary['soft_block_rows']}",
        f"failed_open_rows={summary['failed_open_rows']}",
        f"avg_expectancy_points={summary['avg_expectancy_points']}",
        f"first_event_ts={summary['first_event_ts']}",
        f"last_event_ts={summary['last_event_ts']}",
        f"hours_since_last_event={summary['hours_since_last_event']}",
        flush=True,
    )

    for row in session_rows:
        print(
            "RUNTIME_GOVERNANCE_POPULATION_SESSION",
            f"hour_msk={row['hour_msk']}",
            f"side={row['side']}",
            f"total_rows={row['total_rows']}",
            f"allowed_rows={row['allowed_rows']}",
            f"blocked_rows={row['blocked_rows']}",
            f"avg_expectancy_points={row['avg_expectancy_points']}",
            f"last_event_ts={row['last_event_ts']}",
            flush=True,
        )

    for row in action_rows:
        print(
            "RUNTIME_GOVERNANCE_POPULATION_ACTION",
            f"action={row['action']}",
            f"reason={row['reason']}",
            f"total_rows={row['total_rows']}",
            f"avg_expectancy_points={row['avg_expectancy_points']}",
            f"last_event_ts={row['last_event_ts']}",
            flush=True,
        )

    print(
        f"RUNTIME_GOVERNANCE_POPULATION_STATUS_V1_OK status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
