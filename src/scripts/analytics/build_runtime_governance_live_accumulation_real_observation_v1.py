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
    count(*) FILTER (WHERE action = 'FAILED_OPEN') AS failed_open_rows,
    min(created_at) AS first_event_ts,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_minutes)s * interval '1 minute');
"""


LAST_ROWS_SQL = """
SELECT
    id,
    created_at,
    symbol,
    side,
    allowed,
    action,
    reason,
    session_action,
    strict_reason,
    decay_state,
    expectancy_points,
    closed_trades,
    raw_json
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s
  AND created_at >= now() - (%(window_minutes)s * interval '1 minute')
ORDER BY id DESC
LIMIT 10;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-minutes", type=int, default=60)
    args = parser.parse_args()

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                SUMMARY_SQL,
                {
                    "source": SOURCE,
                    "window_minutes": args.window_minutes,
                },
            )
            summary = dict(cur.fetchone())

            cur.execute(
                LAST_ROWS_SQL,
                {
                    "source": SOURCE,
                    "window_minutes": args.window_minutes,
                },
            )
            rows = [dict(row) for row in cur.fetchall()]

    total_rows = int(summary["total_rows"] or 0)

    status = (
        "REAL_PIPELINE_ACCUMULATION_CONFIRMED"
        if total_rows > 0
        else "NO_REAL_PIPELINE_ROWS_YET"
    )

    print("RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_REAL_OBSERVATION_V1")
    print(
        "RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_REAL_OBSERVATION_STATUS",
        f"status={status}",
        f"git_clean={git_clean()}",
        f"source={SOURCE}",
        f"window_minutes={args.window_minutes}",
        f"total_rows={summary['total_rows']}",
        f"allowed_rows={summary['allowed_rows']}",
        f"blocked_rows={summary['blocked_rows']}",
        f"failed_open_rows={summary['failed_open_rows']}",
        f"first_event_ts={summary['first_event_ts']}",
        f"last_event_ts={summary['last_event_ts']}",
        flush=True,
    )

    for row in rows:
        print(
            "RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_REAL_ROW",
            f"id={row['id']}",
            f"created_at={row['created_at']}",
            f"symbol={row['symbol']}",
            f"side={row['side']}",
            f"allowed={row['allowed']}",
            f"action={row['action']}",
            f"reason={row['reason']}",
            f"session_action={row['session_action']}",
            f"strict_reason={row['strict_reason']}",
            f"decay_state={row['decay_state']}",
            f"expectancy_points={row['expectancy_points']}",
            f"closed_trades={row['closed_trades']}",
            flush=True,
        )

    print(
        f"RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_REAL_OBSERVATION_V1_OK status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
