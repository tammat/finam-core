from __future__ import annotations

import argparse
import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SOURCES = [
    ("real", "paper_pipeline_phase2_runtime"),
    ("forced", "forced_runtime_governance_observation_v1"),
]


SUMMARY_SQL = """
SELECT
    raw_json->>'source' AS source,
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
        extract(epoch from (now() - max(created_at)))::numeric / 3600,
        4
    ) AS hours_since_last_event
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour')
GROUP BY raw_json->>'source';
"""


REASON_SQL = """
SELECT
    action,
    reason,
    session_action,
    strict_reason,
    decay_state,
    count(*) AS total_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    round(avg(expectancy_points)::numeric, 6) AS avg_expectancy_points,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour')
GROUP BY action, reason, session_action, strict_reason, decay_state
ORDER BY total_rows DESC, action, reason
LIMIT 20;
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


COMBINED_SQL = """
SELECT
    raw_json->>'source' AS source,
    count(*) AS total_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    count(*) FILTER (WHERE action = 'SOFT_BLOCK') AS soft_block_rows,
    round(avg(expectancy_points)::numeric, 6) AS avg_expectancy_points,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' IN (
    'paper_pipeline_phase2_runtime',
    'forced_runtime_governance_observation_v1'
)
  AND created_at >= now() - (%(window_hours)s * interval '1 hour')
GROUP BY raw_json->>'source'
ORDER BY source;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def sample_status(total_rows: int, source_kind: str) -> str:
    if total_rows <= 0:
        return "EMPTY"

    if source_kind == "real":
        if total_rows < 10:
            return "EARLY_REAL_SAMPLE"
        if total_rows < 30:
            return "REAL_SAMPLE_BUILDING"
        if total_rows < 50:
            return "REAL_ANALYSIS_READY"
        if total_rows < 100:
            return "REAL_GOOD_SAMPLE"
        return "REAL_STRONG_SAMPLE"

    if total_rows < 10:
        return "EARLY_FORCED_SAMPLE"
    if total_rows < 30:
        return "FORCED_SAMPLE_BUILDING"
    if total_rows < 50:
        return "FORCED_ANALYSIS_READY"
    if total_rows < 100:
        return "FORCED_GOOD_SAMPLE"
    return "FORCED_STRONG_SAMPLE"


def source_note(source_kind: str) -> str:
    if source_kind == "real":
        return "реальные_события_из_paper_pipeline"
    return "диагностические_события_без_заявок"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-hours", type=int, default=24 * 7)
    args = parser.parse_args()

    print("RUNTIME_GOVERNANCE_POPULATION_STATUS_V2")

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(COMBINED_SQL, {"window_hours": args.window_hours})
            combined_rows = [dict(row) for row in cur.fetchall()]

            for row in combined_rows:
                print(
                    "RUNTIME_GOVERNANCE_POPULATION_COMBINED",
                    f"source={row['source']}",
                    f"total_rows={row['total_rows']}",
                    f"allowed_rows={row['allowed_rows']}",
                    f"blocked_rows={row['blocked_rows']}",
                    f"soft_block_rows={row['soft_block_rows']}",
                    f"avg_expectancy_points={row['avg_expectancy_points']}",
                    f"last_event_ts={row['last_event_ts']}",
                    flush=True,
                )

            for source_kind, source in SOURCES:
                params = {
                    "source": source,
                    "window_hours": args.window_hours,
                }

                cur.execute(SUMMARY_SQL, params)
                summary = cur.fetchone()

                if summary is None:
                    total_rows = 0
                    print(
                        "RUNTIME_GOVERNANCE_POPULATION_SOURCE_SUMMARY",
                        f"kind={source_kind}",
                        f"status={sample_status(total_rows, source_kind)}",
                        f"note={source_note(source_kind)}",
                        f"git_clean={git_clean()}",
                        f"source={source}",
                        f"window_hours={args.window_hours}",
                        "total_rows=0",
                        "allowed_rows=0",
                        "blocked_rows=0",
                        "allow_action_rows=0",
                        "soft_block_rows=0",
                        "failed_open_rows=0",
                        "avg_expectancy_points=None",
                        "first_event_ts=None",
                        "last_event_ts=None",
                        "hours_since_last_event=None",
                        flush=True,
                    )
                    continue

                summary = dict(summary)
                total_rows = int(summary["total_rows"] or 0)
                status = sample_status(total_rows, source_kind)

                print(
                    "RUNTIME_GOVERNANCE_POPULATION_SOURCE_SUMMARY",
                    f"kind={source_kind}",
                    f"status={status}",
                    f"note={source_note(source_kind)}",
                    f"git_clean={git_clean()}",
                    f"source={summary['source']}",
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

                cur.execute(SESSION_SQL, params)
                for row in cur.fetchall():
                    row = dict(row)
                    print(
                        "RUNTIME_GOVERNANCE_POPULATION_SOURCE_SESSION",
                        f"kind={source_kind}",
                        f"source={source}",
                        f"hour_msk={row['hour_msk']}",
                        f"side={row['side']}",
                        f"total_rows={row['total_rows']}",
                        f"allowed_rows={row['allowed_rows']}",
                        f"blocked_rows={row['blocked_rows']}",
                        f"avg_expectancy_points={row['avg_expectancy_points']}",
                        f"last_event_ts={row['last_event_ts']}",
                        flush=True,
                    )

                cur.execute(REASON_SQL, params)
                for row in cur.fetchall():
                    row = dict(row)
                    print(
                        "RUNTIME_GOVERNANCE_POPULATION_SOURCE_REASON",
                        f"kind={source_kind}",
                        f"source={source}",
                        f"action={row['action']}",
                        f"reason={row['reason']}",
                        f"session_action={row['session_action']}",
                        f"strict_reason={row['strict_reason']}",
                        f"decay_state={row['decay_state']}",
                        f"total_rows={row['total_rows']}",
                        f"allowed_rows={row['allowed_rows']}",
                        f"blocked_rows={row['blocked_rows']}",
                        f"avg_expectancy_points={row['avg_expectancy_points']}",
                        f"last_event_ts={row['last_event_ts']}",
                        flush=True,
                    )

    print("RUNTIME_GOVERNANCE_POPULATION_STATUS_V2_OK", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
