from __future__ import annotations

import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


WINDOWS = [
    ("1h", "1 hour"),
    ("24h", "24 hours"),
    ("7d", "7 days"),
]


SUMMARY_SQL = """
SELECT
    count(*) AS total_rows,

    count(*) FILTER (
        WHERE allowed = true
    ) AS allowed_rows,

    count(*) FILTER (
        WHERE allowed = false
    ) AS blocked_rows,

    count(*) FILTER (
        WHERE action = 'FAILED_OPEN'
    ) AS failed_open_rows,

    count(*) FILTER (
        WHERE action = 'ALLOW'
    ) AS allow_action_rows,

    count(*) FILTER (
        WHERE action = 'SOFT_BLOCK'
    ) AS soft_block_rows,

    count(*) FILTER (
        WHERE decay_state = 'HEALTHY'
    ) AS healthy_rows,

    count(*) FILTER (
        WHERE decay_state = 'DECAY'
    ) AS decay_rows,

    round(avg(expectancy_points)::numeric, 6)
        AS avg_expectancy_points,

    max(created_at) AS last_event_ts

FROM runtime_governance_live_accumulation_v1

WHERE created_at >= now() - interval %(window)s;
"""


SYMBOL_SQL = """
SELECT
    symbol,
    side,

    count(*) AS total_rows,

    count(*) FILTER (
        WHERE allowed = true
    ) AS allowed_rows,

    count(*) FILTER (
        WHERE allowed = false
    ) AS blocked_rows,

    round(avg(expectancy_points)::numeric, 6)
        AS avg_expectancy_points,

    max(created_at) AS last_event_ts

FROM runtime_governance_live_accumulation_v1

WHERE created_at >= now() - interval %(window)s

GROUP BY symbol, side

ORDER BY total_rows DESC, symbol, side

LIMIT 20;
"""


ACTION_SQL = """
SELECT
    action,
    reason,
    count(*) AS rows_count
FROM runtime_governance_live_accumulation_v1

WHERE created_at >= now() - interval %(window)s

GROUP BY action, reason

ORDER BY rows_count DESC, action, reason

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


def main() -> int:
    print("RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_REPORT_V1")

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:

            for window_key, interval_value in WINDOWS:

                cur.execute(
                    SUMMARY_SQL,
                    {"window": interval_value},
                )

                summary = dict(cur.fetchone())

                print(
                    "RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_SUMMARY",
                    f"window={window_key}",
                    f"total_rows={summary['total_rows']}",
                    f"allowed_rows={summary['allowed_rows']}",
                    f"blocked_rows={summary['blocked_rows']}",
                    f"failed_open_rows={summary['failed_open_rows']}",
                    f"allow_action_rows={summary['allow_action_rows']}",
                    f"soft_block_rows={summary['soft_block_rows']}",
                    f"healthy_rows={summary['healthy_rows']}",
                    f"decay_rows={summary['decay_rows']}",
                    f"avg_expectancy_points={summary['avg_expectancy_points']}",
                    f"last_event_ts={summary['last_event_ts']}",
                    flush=True,
                )

                cur.execute(
                    SYMBOL_SQL,
                    {"window": interval_value},
                )

                symbol_rows = cur.fetchall()

                for row in symbol_rows:
                    row = dict(row)

                    print(
                        "RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_SYMBOL",
                        f"window={window_key}",
                        f"symbol={row['symbol']}",
                        f"side={row['side']}",
                        f"total_rows={row['total_rows']}",
                        f"allowed_rows={row['allowed_rows']}",
                        f"blocked_rows={row['blocked_rows']}",
                        f"avg_expectancy_points={row['avg_expectancy_points']}",
                        f"last_event_ts={row['last_event_ts']}",
                        flush=True,
                    )

                cur.execute(
                    ACTION_SQL,
                    {"window": interval_value},
                )

                action_rows = cur.fetchall()

                for row in action_rows:
                    row = dict(row)

                    print(
                        "RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_ACTION",
                        f"window={window_key}",
                        f"action={row['action']}",
                        f"reason={row['reason']}",
                        f"rows_count={row['rows_count']}",
                        flush=True,
                    )

    status = (
        "LIVE_ACCUMULATION_REPORT_READY"
        if git_clean()
        else "WARN_GIT_DIRTY"
    )

    print(
        "RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_REPORT_STATUS",
        f"status={status}",
        f"git_clean={git_clean()}",
        flush=True,
    )

    print(
        f"RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_REPORT_V1_OK status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
