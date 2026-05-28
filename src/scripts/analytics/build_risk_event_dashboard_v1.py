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
        category,
        severity,
        symbol,
        strategy,
        timeframe,
        decision,
        reason,
        routed,
        channel,
        skipped_reason,
        raw_json,
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


SYSTEM_SQL = CLASSIFIED_CTE + """
SELECT
    count(*) AS total_rows,
    count(*) FILTER (WHERE event_class = 'PRODUCTION_CANDIDATE') AS production_rows,
    count(*) FILTER (WHERE event_class = 'TEST') AS test_rows,
    count(*) FILTER (WHERE event_class = 'UNKNOWN') AS unknown_rows,
    count(*) FILTER (WHERE severity = 'CRITICAL') AS critical_rows,
    count(*) FILTER (WHERE severity = 'WARNING') AS warning_rows,
    count(*) FILTER (WHERE routed = true) AS routed_rows,
    count(*) FILTER (WHERE skipped_reason IS NOT NULL) AS skipped_rows,
    max(created_at) AS last_event_ts
FROM classified;
"""


TODAY_SQL = CLASSIFIED_CTE + """
SELECT
    count(*) AS total_today,
    count(*) FILTER (WHERE event_class = 'PRODUCTION_CANDIDATE') AS production_today,
    count(*) FILTER (WHERE event_class = 'TEST') AS test_today,
    count(*) FILTER (WHERE event_class = 'UNKNOWN') AS unknown_today,
    count(*) FILTER (WHERE severity = 'CRITICAL') AS critical_today,
    count(*) FILTER (WHERE severity = 'WARNING') AS warning_today,
    count(*) FILTER (WHERE routed = true) AS routed_today,
    count(*) FILTER (WHERE skipped_reason IS NOT NULL) AS skipped_today
FROM classified
WHERE event_date = (now() AT TIME ZONE 'Europe/Moscow')::date;
"""


TOP_REASONS_SQL = CLASSIFIED_CTE + """
SELECT
    reason,
    severity,
    count(*) AS events,
    max(created_at) AS last_seen
FROM classified
WHERE event_class = 'PRODUCTION_CANDIDATE'
GROUP BY reason, severity
ORDER BY events DESC, last_seen DESC
LIMIT 10;
"""


TOP_SYMBOLS_SQL = CLASSIFIED_CTE + """
SELECT
    symbol,
    count(*) AS events,
    count(*) FILTER (WHERE severity = 'CRITICAL') AS critical_events,
    count(*) FILTER (WHERE routed = true) AS routed_events,
    max(created_at) AS last_seen
FROM classified
WHERE event_class = 'PRODUCTION_CANDIDATE'
GROUP BY symbol
ORDER BY events DESC, last_seen DESC
LIMIT 10;
"""


LAST_EVENTS_SQL = CLASSIFIED_CTE + """
SELECT
    id,
    created_at,
    event_class,
    category,
    severity,
    symbol,
    strategy,
    timeframe,
    decision,
    reason,
    routed,
    channel,
    skipped_reason
FROM classified
ORDER BY created_at DESC, id DESC
LIMIT 10;
"""


def git_is_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def status_from(system: dict, today: dict, git_clean: bool) -> str:
    if not git_clean:
        return "WARN_GIT_DIRTY"

    if int(system["unknown_rows"] or 0) > 0:
        return "WARN_UNKNOWN_ROWS"

    if int(system["test_rows"] or 0) > 0:
        return "WARN_TEST_ROWS"

    if int(system["total_rows"] or 0) <= 0:
        return "WARN_NO_RISK_EVENTS"

    if int(today["unknown_today"] or 0) > 0:
        return "WARN_UNKNOWN_TODAY"

    return "OK"


def fetch_all(cur, sql: str) -> list[dict]:
    cur.execute(sql)
    return [dict(r) for r in cur.fetchall()]


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()
    git_clean = git_is_clean()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SYSTEM_SQL)
            system = dict(cur.fetchone())

            cur.execute(TODAY_SQL)
            today = dict(cur.fetchone())

            top_reasons = fetch_all(cur, TOP_REASONS_SQL)
            top_symbols = fetch_all(cur, TOP_SYMBOLS_SQL)
            last_events = fetch_all(cur, LAST_EVENTS_SQL)

    status = status_from(system=system, today=today, git_clean=git_clean)

    print("RISK_EVENT_DASHBOARD_V1", flush=True)

    print(
        "RISK_EVENT_DASHBOARD_SYSTEM",
        f"status={status}",
        f"git_clean={git_clean}",
        f"total_rows={system['total_rows']}",
        f"production_rows={system['production_rows']}",
        f"test_rows={system['test_rows']}",
        f"unknown_rows={system['unknown_rows']}",
        f"critical_rows={system['critical_rows']}",
        f"warning_rows={system['warning_rows']}",
        f"routed_rows={system['routed_rows']}",
        f"skipped_rows={system['skipped_rows']}",
        f"last_event_ts={system['last_event_ts']}",
        flush=True,
    )

    print(
        "RISK_EVENT_DASHBOARD_TODAY",
        f"total_today={today['total_today']}",
        f"production_today={today['production_today']}",
        f"test_today={today['test_today']}",
        f"unknown_today={today['unknown_today']}",
        f"critical_today={today['critical_today']}",
        f"warning_today={today['warning_today']}",
        f"routed_today={today['routed_today']}",
        f"skipped_today={today['skipped_today']}",
        flush=True,
    )

    for r in top_reasons:
        print(
            "RISK_EVENT_DASHBOARD_TOP_REASON",
            f"reason={r['reason']}",
            f"severity={r['severity']}",
            f"events={r['events']}",
            f"last_seen={r['last_seen']}",
            flush=True,
        )

    for r in top_symbols:
        print(
            "RISK_EVENT_DASHBOARD_TOP_SYMBOL",
            f"symbol={r['symbol']}",
            f"events={r['events']}",
            f"critical={r['critical_events']}",
            f"routed={r['routed_events']}",
            f"last_seen={r['last_seen']}",
            flush=True,
        )

    for r in last_events:
        print(
            "RISK_EVENT_DASHBOARD_LAST_EVENT",
            f"id={r['id']}",
            f"ts={r['created_at']}",
            f"class={r['event_class']}",
            f"category={r['category']}",
            f"severity={r['severity']}",
            f"symbol={r['symbol']}",
            f"strategy={r['strategy']}",
            f"timeframe={r['timeframe']}",
            f"decision={r['decision']}",
            f"reason={r['reason']}",
            f"routed={r['routed']}",
            f"channel={r['channel']}",
            f"skipped_reason={r['skipped_reason']}",
            flush=True,
        )

    print(
        "RISK_EVENT_DASHBOARD_V1_OK",
        f"status={status}",
        f"top_reasons={len(top_reasons)}",
        f"top_symbols={len(top_symbols)}",
        f"last_events={len(last_events)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
