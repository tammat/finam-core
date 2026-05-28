from __future__ import annotations

import os
import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


CLASSIFIED_CTE = """
WITH classified AS (
    SELECT
        id,
        created_at,
        (created_at AT TIME ZONE 'Europe/Moscow')::date AS event_date,
        severity,
        symbol,
        strategy,
        timeframe,
        decision,
        reason,
        routed,
        skipped_reason,

        COALESCE(
            raw_json->>'regime',
            raw_json->>'market_regime',
            raw_json->>'regime_name',
            'UNKNOWN_REGIME'
        ) AS regime,

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
"""


SUMMARY_SQL = CLASSIFIED_CTE + """
SELECT
    regime,
    count(*) AS total_events,
    count(*) FILTER (WHERE event_class = 'PRODUCTION_CANDIDATE') AS production_events,
    count(*) FILTER (WHERE severity = 'CRITICAL') AS critical_events,
    count(*) FILTER (WHERE severity = 'WARNING') AS warning_events,
    count(*) FILTER (WHERE routed = true) AS routed_events,
    count(*) FILTER (WHERE skipped_reason IS NOT NULL) AS skipped_events,
    count(DISTINCT symbol) AS unique_symbols,
    count(DISTINCT strategy) AS unique_strategies,
    count(DISTINCT reason) AS unique_reasons,
    min(created_at) AS first_seen,
    max(created_at) AS last_seen
FROM classified
GROUP BY regime
ORDER BY total_events DESC, last_seen DESC;
"""


REASON_SQL = CLASSIFIED_CTE + """
SELECT
    regime,
    reason,
    count(*) AS total_events,
    count(*) FILTER (WHERE severity = 'CRITICAL') AS critical_events,
    max(created_at) AS last_seen
FROM classified
GROUP BY regime, reason
ORDER BY total_events DESC, last_seen DESC
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


def determine_status(*, git_is_clean: bool, unknown_regimes: int, total_events: int) -> str:
    if not git_is_clean:
        return "WARN_GIT_DIRTY"
    if unknown_regimes > 0:
        return "WARN_UNKNOWN_REGIME"
    if total_events == 0:
        return "WARN_EMPTY"
    return "OK"


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SUMMARY_SQL)
            summary_rows = [dict(r) for r in cur.fetchall()]

            cur.execute(REASON_SQL)
            reason_rows = [dict(r) for r in cur.fetchall()]

    total_events = sum(int(r["total_events"]) for r in summary_rows)
    unknown_regimes = sum(
        int(r["total_events"])
        for r in summary_rows
        if r["regime"] == "UNKNOWN_REGIME"
    )

    git_is_clean = git_clean()
    status = determine_status(
        git_is_clean=git_is_clean,
        unknown_regimes=unknown_regimes,
        total_events=total_events,
    )

    print("RUNTIME_RISK_REGIME_STATS_V1", flush=True)
    print(
        "RUNTIME_RISK_REGIME_STATUS",
        f"status={status}",
        f"git_clean={git_is_clean}",
        f"regimes={len(summary_rows)}",
        f"total_events={total_events}",
        f"unknown_regimes={unknown_regimes}",
        flush=True,
    )

    for row in summary_rows:
        print(
            "RUNTIME_RISK_REGIME_ROW",
            f"regime={row['regime']}",
            f"total_events={row['total_events']}",
            f"production_events={row['production_events']}",
            f"critical_events={row['critical_events']}",
            f"warning_events={row['warning_events']}",
            f"routed_events={row['routed_events']}",
            f"skipped_events={row['skipped_events']}",
            f"unique_symbols={row['unique_symbols']}",
            f"unique_strategies={row['unique_strategies']}",
            f"unique_reasons={row['unique_reasons']}",
            f"first_seen={row['first_seen']}",
            f"last_seen={row['last_seen']}",
            flush=True,
        )

    for row in reason_rows:
        print(
            "RUNTIME_RISK_REGIME_REASON_ROW",
            f"regime={row['regime']}",
            f"reason={row['reason']}",
            f"total_events={row['total_events']}",
            f"critical_events={row['critical_events']}",
            f"last_seen={row['last_seen']}",
            flush=True,
        )

    print(
        "RUNTIME_RISK_REGIME_STATS_V1_OK",
        f"status={status}",
        f"regimes={len(summary_rows)}",
        f"reason_rows={len(reason_rows)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
