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
    min(expectancy_points) AS min_expectancy_points,
    max(expectancy_points) AS max_expectancy_points,
    min(created_at) AS first_event_ts,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour')
GROUP BY raw_json->>'source';
"""


SESSION_SIDE_SQL = """
SELECT
    hour_msk,
    side,
    count(*) AS total_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    round(
        count(*) FILTER (WHERE allowed = true)::numeric / NULLIF(count(*), 0),
        6
    ) AS allow_rate,
    round(avg(expectancy_points)::numeric, 6) AS avg_expectancy_points,
    min(expectancy_points) AS min_expectancy_points,
    max(expectancy_points) AS max_expectancy_points,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour')
GROUP BY hour_msk, side
ORDER BY total_rows DESC, hour_msk, side
LIMIT 50;
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
    min(expectancy_points) AS min_expectancy_points,
    max(expectancy_points) AS max_expectancy_points,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour')
GROUP BY action, reason, session_action, strict_reason, decay_state
ORDER BY total_rows DESC, action, reason
LIMIT 50;
"""


SYMBOL_SQL = """
SELECT
    symbol,
    side,
    count(*) AS total_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    round(avg(expectancy_points)::numeric, 6) AS avg_expectancy_points,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_hours)s * interval '1 hour')
GROUP BY symbol, side
ORDER BY total_rows DESC, symbol, side
LIMIT 50;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def sample_status(kind: str, total_rows: int) -> str:
    prefix = "REAL" if kind == "real" else "FORCED"

    if total_rows <= 0:
        return f"{prefix}_NO_DATA"
    if total_rows < 10:
        return f"{prefix}_EARLY_SAMPLE"
    if total_rows < 30:
        return f"{prefix}_BUILDING"
    if total_rows < 50:
        return f"{prefix}_ANALYSIS_READY"
    if total_rows < 100:
        return f"{prefix}_GOOD_SAMPLE"
    return f"{prefix}_STRONG_SAMPLE"


def effectiveness_status(
    *,
    kind: str,
    total_rows: int,
    blocked_rows: int,
    avg_expectancy,
) -> str:
    if total_rows <= 0:
        return "NO_DATA"

    if kind == "real" and total_rows < 30:
        return "INSUFFICIENT_REAL_SAMPLE"

    if kind == "forced" and total_rows < 30:
        return "FORCED_SAMPLE_BUILDING"

    if avg_expectancy is None:
        if blocked_rows > 0:
            return "STRUCTURAL_BLOCKING_ONLY_NO_EXPECTANCY"
        return "NO_EXPECTANCY"

    avg = float(avg_expectancy)

    if blocked_rows > 0 and avg < 0:
        return "BLOCKING_NEGATIVE_EXPECTANCY_CONTEXT"
    if avg >= 0:
        return "NEUTRAL_OR_POSITIVE_CONTEXT"

    return "REVIEW_REQUIRED"


def print_empty(kind: str, source: str, window_hours: int) -> None:
    print(
        "RUNTIME_GOVERNANCE_EFFECTIVENESS_V2_SOURCE_SUMMARY",
        f"kind={kind}",
        f"sample_status={sample_status(kind, 0)}",
        "effectiveness_status=NO_DATA",
        f"git_clean={git_clean()}",
        f"source={source}",
        f"window_hours={window_hours}",
        "total_rows=0",
        "allowed_rows=0",
        "blocked_rows=0",
        "allow_action_rows=0",
        "soft_block_rows=0",
        "failed_open_rows=0",
        "avg_expectancy_points=None",
        "min_expectancy_points=None",
        "max_expectancy_points=None",
        "first_event_ts=None",
        "last_event_ts=None",
        flush=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-hours", type=int, default=24 * 7)
    args = parser.parse_args()

    print("RUNTIME_GOVERNANCE_EFFECTIVENESS_V2")

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            for kind, source in SOURCES:
                params = {
                    "source": source,
                    "window_hours": args.window_hours,
                }

                cur.execute(SUMMARY_SQL, params)
                summary = cur.fetchone()

                if summary is None:
                    print_empty(kind, source, args.window_hours)
                    continue

                summary = dict(summary)

                total_rows = int(summary["total_rows"] or 0)
                blocked_rows = int(summary["blocked_rows"] or 0)
                avg_expectancy = summary["avg_expectancy_points"]

                print(
                    "RUNTIME_GOVERNANCE_EFFECTIVENESS_V2_SOURCE_SUMMARY",
                    f"kind={kind}",
                    f"sample_status={sample_status(kind, total_rows)}",
                    f"effectiveness_status={effectiveness_status(kind=kind, total_rows=total_rows, blocked_rows=blocked_rows, avg_expectancy=avg_expectancy)}",
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
                    f"min_expectancy_points={summary['min_expectancy_points']}",
                    f"max_expectancy_points={summary['max_expectancy_points']}",
                    f"first_event_ts={summary['first_event_ts']}",
                    f"last_event_ts={summary['last_event_ts']}",
                    flush=True,
                )

                cur.execute(SESSION_SIDE_SQL, params)
                for row in cur.fetchall():
                    row = dict(row)
                    print(
                        "RUNTIME_GOVERNANCE_EFFECTIVENESS_V2_SESSION_SIDE",
                        f"kind={kind}",
                        f"source={source}",
                        f"hour_msk={row['hour_msk']}",
                        f"side={row['side']}",
                        f"total_rows={row['total_rows']}",
                        f"allowed_rows={row['allowed_rows']}",
                        f"blocked_rows={row['blocked_rows']}",
                        f"allow_rate={row['allow_rate']}",
                        f"avg_expectancy_points={row['avg_expectancy_points']}",
                        f"min_expectancy_points={row['min_expectancy_points']}",
                        f"max_expectancy_points={row['max_expectancy_points']}",
                        f"last_event_ts={row['last_event_ts']}",
                        flush=True,
                    )

                cur.execute(REASON_SQL, params)
                for row in cur.fetchall():
                    row = dict(row)
                    print(
                        "RUNTIME_GOVERNANCE_EFFECTIVENESS_V2_REASON",
                        f"kind={kind}",
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
                        f"min_expectancy_points={row['min_expectancy_points']}",
                        f"max_expectancy_points={row['max_expectancy_points']}",
                        f"last_event_ts={row['last_event_ts']}",
                        flush=True,
                    )

                cur.execute(SYMBOL_SQL, params)
                for row in cur.fetchall():
                    row = dict(row)
                    print(
                        "RUNTIME_GOVERNANCE_EFFECTIVENESS_V2_SYMBOL",
                        f"kind={kind}",
                        f"source={source}",
                        f"symbol={row['symbol']}",
                        f"side={row['side']}",
                        f"total_rows={row['total_rows']}",
                        f"allowed_rows={row['allowed_rows']}",
                        f"blocked_rows={row['blocked_rows']}",
                        f"avg_expectancy_points={row['avg_expectancy_points']}",
                        f"last_event_ts={row['last_event_ts']}",
                        flush=True,
                    )

    print("RUNTIME_GOVERNANCE_EFFECTIVENESS_V2_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
