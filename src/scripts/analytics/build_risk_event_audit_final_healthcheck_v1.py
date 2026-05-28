from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SUMMARY_SQL = """
SELECT count(*) AS total_rows
FROM risk_event_audit_v1;
"""

PRODUCTION_SQL = """
WITH classified AS (
    SELECT
        CASE
            WHEN position('"test"' in raw_json::text) > 0
              OR position('wire_' in raw_json::text) > 0
              OR position('test' in lower(reason)) > 0
                THEN 'TEST'
            WHEN raw_json->>'source' = 'risk_notification_bridge_v1'
                THEN 'PRODUCTION_CANDIDATE'
            ELSE 'UNKNOWN'
        END AS event_class
    FROM risk_event_audit_v1
)
SELECT
    count(*) FILTER (
        WHERE event_class = 'PRODUCTION_CANDIDATE'
    ) AS production_rows,

    count(*) FILTER (
        WHERE event_class = 'TEST'
    ) AS test_rows,

    count(*) FILTER (
        WHERE event_class = 'UNKNOWN'
    ) AS unknown_rows
FROM classified;
"""

HEALTH_SQL = """
SELECT
    count(*) FILTER (
        WHERE severity = 'CRITICAL'
    ) AS critical_rows,

    count(*) FILTER (
        WHERE routed = true
    ) AS routed_rows,

    count(*) FILTER (
        WHERE skipped_reason IS NOT NULL
    ) AS skipped_rows,

    max(created_at) AS last_event_ts
FROM risk_event_audit_v1;
"""


@dataclass(frozen=True)
class FinalHealthResult:
    total_rows: int
    production_rows: int
    test_rows: int
    unknown_rows: int
    critical_rows: int
    routed_rows: int
    skipped_rows: int
    last_event_ts: str | None
    git_clean: bool


def git_is_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.stdout.strip() == ""


def load_metrics() -> FinalHealthResult:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SUMMARY_SQL)
            summary = cur.fetchone()

            cur.execute(PRODUCTION_SQL)
            production = cur.fetchone()

            cur.execute(HEALTH_SQL)
            health = cur.fetchone()

    return FinalHealthResult(
        total_rows=int(summary["total_rows"] or 0),
        production_rows=int(production["production_rows"] or 0),
        test_rows=int(production["test_rows"] or 0),
        unknown_rows=int(production["unknown_rows"] or 0),
        critical_rows=int(health["critical_rows"] or 0),
        routed_rows=int(health["routed_rows"] or 0),
        skipped_rows=int(health["skipped_rows"] or 0),
        last_event_ts=(
            str(health["last_event_ts"])
            if health["last_event_ts"] is not None
            else None
        ),
        git_clean=git_is_clean(),
    )


def determine_status(result: FinalHealthResult) -> str:
    if result.unknown_rows > 0:
        return "WARN_UNKNOWN_ROWS"

    if result.test_rows > 0:
        return "WARN_TEST_ROWS"

    if not result.git_clean:
        return "WARN_GIT_DIRTY"

    if result.total_rows <= 0:
        return "WARN_NO_ROWS"

    return "OK"


def main() -> int:
    result = load_metrics()
    status = determine_status(result)

    print("RISK_EVENT_AUDIT_FINAL_HEALTHCHECK_V1", flush=True)

    print(
        "RISK_EVENT_AUDIT_FINAL_HEALTHCHECK_STATUS",
        f"status={status}",
        f"total_rows={result.total_rows}",
        f"production_rows={result.production_rows}",
        f"test_rows={result.test_rows}",
        f"unknown_rows={result.unknown_rows}",
        f"critical_rows={result.critical_rows}",
        f"routed_rows={result.routed_rows}",
        f"skipped_rows={result.skipped_rows}",
        f"git_clean={result.git_clean}",
        f"last_event_ts={result.last_event_ts}",
        flush=True,
    )

    print(
        "RISK_EVENT_AUDIT_FINAL_HEALTHCHECK_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
