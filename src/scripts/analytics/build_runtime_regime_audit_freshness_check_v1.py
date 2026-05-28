from __future__ import annotations

import os
import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SQL = """
WITH classified AS (
    SELECT
        id,
        created_at,
        symbol,
        strategy,
        timeframe,
        decision,
        reason,
        severity,
        raw_json,

        COALESCE(
            raw_json->>'regime',
            raw_json->>'market_regime',
            raw_json->>'regime_name',
            'UNKNOWN_REGIME'
        ) AS regime,

        raw_json->>'trend' AS trend,
        raw_json->>'volatility' AS volatility,
        raw_json->>'atr' AS atr,
        raw_json->>'atr_pct' AS atr_pct,
        raw_json->>'price' AS price,
        raw_json->>'tradable' AS tradable,

        CASE
            WHEN raw_json::text LIKE '%"test"%'
              OR raw_json::text LIKE '%wire_%'
              OR lower(reason) LIKE '%test%'
                THEN 'TEST'

            WHEN raw_json->>'source' = 'risk_notification_bridge_v1'
                THEN 'PRODUCTION_CANDIDATE'

            ELSE 'UNKNOWN'
        END AS event_class

    FROM risk_event_audit_v1
),
summary AS (
    SELECT
        count(*) AS total_events,
        count(*) FILTER (WHERE event_class = 'PRODUCTION_CANDIDATE') AS production_events,
        count(*) FILTER (WHERE event_class = 'TEST') AS test_events,
        count(*) FILTER (WHERE event_class = 'UNKNOWN') AS unknown_events,

        count(*) FILTER (
            WHERE event_class = 'PRODUCTION_CANDIDATE'
              AND regime = 'UNKNOWN_REGIME'
        ) AS unknown_regime_events,

        count(*) FILTER (
            WHERE event_class = 'PRODUCTION_CANDIDATE'
              AND regime <> 'UNKNOWN_REGIME'
        ) AS regime_enriched_events,

        count(*) FILTER (
            WHERE event_class = 'PRODUCTION_CANDIDATE'
              AND created_at >= TIMESTAMPTZ '2026-05-28 12:03:24.127853+00'
        ) AS events_after_runtime_wire,

        count(*) FILTER (
            WHERE event_class = 'PRODUCTION_CANDIDATE'
              AND created_at >= TIMESTAMPTZ '2026-05-28 12:03:24.127853+00'
              AND regime <> 'UNKNOWN_REGIME'
        ) AS enriched_after_runtime_wire,

        count(*) FILTER (
            WHERE event_class = 'PRODUCTION_CANDIDATE'
              AND created_at >= TIMESTAMPTZ '2026-05-28 12:03:24.127853+00'
              AND regime = 'UNKNOWN_REGIME'
        ) AS unknown_after_runtime_wire,

        max(created_at) AS last_event_ts,
        max(created_at) FILTER (
            WHERE event_class = 'PRODUCTION_CANDIDATE'
              AND regime <> 'UNKNOWN_REGIME'
        ) AS last_enriched_event_ts
    FROM classified
)
SELECT * FROM summary;
"""


DETAIL_SQL = """
SELECT
    id,
    created_at,
    symbol,
    strategy,
    timeframe,
    decision,
    reason,
    severity,
    COALESCE(
        raw_json->>'regime',
        raw_json->>'market_regime',
        raw_json->>'regime_name',
        'UNKNOWN_REGIME'
    ) AS regime,
    raw_json->>'trend' AS trend,
    raw_json->>'volatility' AS volatility,
    raw_json->>'atr' AS atr,
    raw_json->>'atr_pct' AS atr_pct,
    raw_json->>'price' AS price,
    raw_json->>'tradable' AS tradable
FROM risk_event_audit_v1
ORDER BY created_at DESC, id DESC
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


def determine_status(row: dict, clean: bool) -> str:
    if not clean:
        return "WARN_GIT_DIRTY"

    if int(row["test_events"] or 0) > 0:
        return "WARN_TEST_EVENTS"

    if int(row["unknown_events"] or 0) > 0:
        return "WARN_UNKNOWN_EVENTS"

    if int(row["events_after_runtime_wire"] or 0) == 0:
        return "WAITING_FOR_NEW_RUNTIME_RISK_EVENT"

    if int(row["unknown_after_runtime_wire"] or 0) > 0:
        return "WARN_NEW_EVENTS_WITHOUT_REGIME"

    if int(row["enriched_after_runtime_wire"] or 0) > 0:
        return "OK"

    return "WAITING_FOR_ENRICHED_RUNTIME_RISK_EVENT"


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            row = dict(cur.fetchone())

            cur.execute(DETAIL_SQL)
            details = [dict(r) for r in cur.fetchall()]

    clean = git_clean()
    status = determine_status(row, clean)

    print("RUNTIME_REGIME_AUDIT_FRESHNESS_CHECK_V1", flush=True)

    print(
        "RUNTIME_REGIME_AUDIT_FRESHNESS_STATUS",
        f"status={status}",
        f"git_clean={clean}",
        f"total_events={row['total_events']}",
        f"production_events={row['production_events']}",
        f"test_events={row['test_events']}",
        f"unknown_events={row['unknown_events']}",
        f"unknown_regime_events={row['unknown_regime_events']}",
        f"regime_enriched_events={row['regime_enriched_events']}",
        f"events_after_runtime_wire={row['events_after_runtime_wire']}",
        f"enriched_after_runtime_wire={row['enriched_after_runtime_wire']}",
        f"unknown_after_runtime_wire={row['unknown_after_runtime_wire']}",
        f"last_event_ts={row['last_event_ts']}",
        f"last_enriched_event_ts={row['last_enriched_event_ts']}",
        flush=True,
    )

    for r in details:
        print(
            "RUNTIME_REGIME_AUDIT_FRESHNESS_ROW",
            f"id={r['id']}",
            f"ts={r['created_at']}",
            f"symbol={r['symbol']}",
            f"strategy={r['strategy']}",
            f"timeframe={r['timeframe']}",
            f"decision={r['decision']}",
            f"reason={r['reason']}",
            f"severity={r['severity']}",
            f"regime={r['regime']}",
            f"trend={r['trend']}",
            f"volatility={r['volatility']}",
            f"atr={r['atr']}",
            f"atr_pct={r['atr_pct']}",
            f"price={r['price']}",
            f"tradable={r['tradable']}",
            flush=True,
        )

    print(
        "RUNTIME_REGIME_AUDIT_FRESHNESS_CHECK_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
