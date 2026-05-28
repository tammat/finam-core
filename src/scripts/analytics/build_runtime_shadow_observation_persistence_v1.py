from __future__ import annotations

import subprocess

import psycopg

from finam_core.analytics.runtime_shadow_observation_persistence_v1 import (
    RuntimeShadowObservationPersistenceV1,
    RuntimeShadowPersistenceRowV1,
)
from finam_core.analytics.statistics_repository import build_psycopg_url


COUNT_SQL = """
SELECT count(*) AS rows
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
    persistence = RuntimeShadowObservationPersistenceV1()
    persistence.ensure_table()

    persistence.persist(
        RuntimeShadowPersistenceRowV1(
            symbol="BR_ROLLING@RTSX",
            side="BUY",
            hour_msk=19,
            expectancy_points=-0.0486,
            pnl_points=-92.75,
            closed_trades=86,
            decay_state="DECAY",
            shadow_block_candidate=True,
        )
    )

    persistence.persist(
        RuntimeShadowPersistenceRowV1(
            symbol="BR_ROLLING@RTSX",
            side="BUY",
            hour_msk=8,
            expectancy_points=0.218,
            pnl_points=84.11,
            closed_trades=46,
            decay_state="HEALTHY",
            shadow_block_candidate=False,
        )
    )

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(COUNT_SQL)
            rows = cur.fetchone()[0]

    status = "OK" if git_clean() else "WARN_GIT_DIRTY"

    print("RUNTIME_SHADOW_OBSERVATION_PERSISTENCE_V1", flush=True)
    print(
        "RUNTIME_SHADOW_OBSERVATION_PERSISTENCE_STATUS",
        f"status={status}",
        f"git_clean={git_clean()}",
        f"rows={rows}",
        flush=True,
    )
    print(
        "RUNTIME_SHADOW_OBSERVATION_PERSISTENCE_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
