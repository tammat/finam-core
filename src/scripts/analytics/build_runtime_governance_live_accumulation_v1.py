from __future__ import annotations

import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.execution.runtime_governance_live_accumulation_v1 import (
    RuntimeGovernanceLiveAccumulatorV1,
    RuntimeGovernanceLiveDecisionV1,
)


TEST_SOURCE = "runtime_governance_live_accumulation_v1_test"


DELETE_TEST_SQL = """
DELETE FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s;
"""


SUMMARY_SQL = """
SELECT
    count(*) AS total_rows,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    count(*) FILTER (WHERE action = 'FAILED_OPEN') AS failed_open_rows,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1;
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
    accumulator = RuntimeGovernanceLiveAccumulatorV1()
    accumulator.ensure_schema()

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(DELETE_TEST_SQL, {"source": TEST_SOURCE})
        conn.commit()

    accumulator.append(
        RuntimeGovernanceLiveDecisionV1(
            symbol="BR_ROLLING@RTSX",
            side="BUY",
            hour_msk=10,
            allowed=True,
            action="ALLOW",
            reason="runtime_edge_governance_allow",
            session_action="ALLOW",
            strict_reason="strict_mode_positive_expectancy",
            decay_state="HEALTHY",
            expectancy_points=0.0533,
            closed_trades=123,
            raw_json={"source": TEST_SOURCE},
        )
    )

    accumulator.append(
        RuntimeGovernanceLiveDecisionV1(
            symbol="BR_ROLLING@RTSX",
            side="BUY",
            hour_msk=19,
            allowed=False,
            action="SOFT_BLOCK",
            reason="session_side_gate_block",
            session_action="BLOCK",
            strict_reason=None,
            decay_state="DECAY",
            expectancy_points=-0.0486,
            closed_trades=86,
            raw_json={"source": TEST_SOURCE},
        )
    )

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SUMMARY_SQL)
            row = dict(cur.fetchone())

    status = "LIVE_ACCUMULATION_READY" if git_clean() else "WARN_GIT_DIRTY"

    print("RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_V1", flush=True)
    print(
        "RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_STATUS",
        f"status={status}",
        f"git_clean={git_clean()}",
        f"total_rows={row['total_rows']}",
        f"allowed_rows={row['allowed_rows']}",
        f"blocked_rows={row['blocked_rows']}",
        f"failed_open_rows={row['failed_open_rows']}",
        f"last_event_ts={row['last_event_ts']}",
        flush=True,
    )
    print(
        f"RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_V1_OK status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
