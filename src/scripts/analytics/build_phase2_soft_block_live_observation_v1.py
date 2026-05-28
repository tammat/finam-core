from __future__ import annotations

import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SQL = """
SELECT
    count(*) FILTER (
        WHERE created_at >= now() - interval '24 hours'
    ) AS events_24h,

    count(*) FILTER (
        WHERE created_at >= now() - interval '24 hours'
          AND raw_json->>'source' = 'runtime_shadow_observation_persistence_v1'
    ) AS shadow_events_24h,

    count(*) FILTER (
        WHERE created_at >= now() - interval '24 hours'
          AND shadow_block_candidate = true
    ) AS shadow_block_candidates_24h,

    count(*) FILTER (
        WHERE created_at >= now() - interval '24 hours'
          AND decay_state = 'HEALTHY'
    ) AS healthy_events_24h,

    count(*) FILTER (
        WHERE created_at >= now() - interval '24 hours'
          AND decay_state = 'DECAY'
    ) AS decay_events_24h,

    max(created_at) AS last_event_ts
FROM runtime_shadow_observation_v1;
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
    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            row = dict(cur.fetchone())

    events_24h = int(row["events_24h"] or 0)

    status = "LIVE_OBSERVATION_READY"

    if not git_clean():
        status = "WARN_GIT_DIRTY"
    elif events_24h == 0:
        status = "LIVE_OBSERVATION_EMPTY"

    print("PHASE2_SOFT_BLOCK_LIVE_OBSERVATION_V1", flush=True)

    print(
        "PHASE2_SOFT_BLOCK_LIVE_OBSERVATION_STATUS",
        f"status={status}",
        f"git_clean={git_clean()}",
        f"events_24h={row['events_24h']}",
        f"shadow_events_24h={row['shadow_events_24h']}",
        f"shadow_block_candidates_24h={row['shadow_block_candidates_24h']}",
        f"healthy_events_24h={row['healthy_events_24h']}",
        f"decay_events_24h={row['decay_events_24h']}",
        f"last_event_ts={row['last_event_ts']}",
        flush=True,
    )

    print(
        "PHASE2_SOFT_BLOCK_LIVE_OBSERVATION_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
