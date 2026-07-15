from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "FORWARD_EDGE_CONTEXT_BACKFILL_V1"
MOSCOW = ZoneInfo("Europe/Moscow")


def session_code(ts: datetime) -> str:
    hour = ts.astimezone(MOSCOW).hour
    if 7 <= hour < 10:
        return "PREMARKET"
    if 10 <= hour < 14:
        return "MORNING"
    if 14 <= hour < 19:
        return "DAY"
    if 19 <= hour < 24:
        return "EVENING"
    return "OVERNIGHT"


def main() -> int:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT analytics.forward_edge_baseline_cohort_id_v1() AS cohort_id")
            row = cur.fetchone()
            cohort_id = row["cohort_id"] if row else None
            if not cohort_id:
                print("cohort=none")
                print("VERDICT=FORWARD_EDGE_CONTEXT_BACKFILL_V1_NO_COHORT")
                return 0

            cur.execute("""
                UPDATE analytics.forward_edge_observation_v1
                SET session_code = CASE
                    WHEN extract(hour FROM signal_ts AT TIME ZONE 'Europe/Moscow') BETWEEN 7 AND 9 THEN 'PREMARKET'
                    WHEN extract(hour FROM signal_ts AT TIME ZONE 'Europe/Moscow') BETWEEN 10 AND 13 THEN 'MORNING'
                    WHEN extract(hour FROM signal_ts AT TIME ZONE 'Europe/Moscow') BETWEEN 14 AND 18 THEN 'DAY'
                    WHEN extract(hour FROM signal_ts AT TIME ZONE 'Europe/Moscow') BETWEEN 19 AND 23 THEN 'EVENING'
                    ELSE 'OVERNIGHT'
                END,
                source_version = %s
                WHERE cohort_id = %s
                  AND (session_code IS NULL OR session_code IN ('', 'UNKNOWN'))
            """, (SOURCE_VERSION, cohort_id))
            sessions_updated = cur.rowcount

            cur.execute("""
                WITH matches AS (
                    SELECT o.observation_id, r.regime
                    FROM analytics.forward_edge_observation_v1 o
                    JOIN LATERAL (
                        SELECT s.regime
                        FROM public.analytics_regime_snapshots_v2 s
                        WHERE s.symbol = o.symbol
                          AND s.timeframe = o.timeframe
                          AND s.ts <= o.signal_ts
                          AND s.ts >= o.signal_ts - interval '15 minutes'
                        ORDER BY s.ts DESC
                        LIMIT 1
                    ) r ON true
                    WHERE o.cohort_id = %s
                      AND (o.regime_code IS NULL OR o.regime_code IN ('', 'UNKNOWN'))
                )
                UPDATE analytics.forward_edge_observation_v1 o
                SET regime_code = matches.regime,
                    data_quality_status = CASE
                        WHEN o.data_quality_status = 'REGIME_MISSING_COST_PENDING'
                            THEN 'REGIME_ATTRIBUTED_COST_PENDING'
                        ELSE o.data_quality_status
                    END,
                    source_version = %s
                FROM matches
                WHERE o.observation_id = matches.observation_id
            """, (cohort_id, SOURCE_VERSION))
            regimes_updated = cur.rowcount

            cur.execute("""
                SELECT
                    count(*) FILTER (WHERE regime_code IS NULL OR regime_code IN ('', 'UNKNOWN')) AS regime_missing,
                    count(*) FILTER (WHERE session_code IS NULL OR session_code IN ('', 'UNKNOWN')) AS session_missing
                FROM analytics.forward_edge_observation_v1
                WHERE cohort_id = %s
            """, (cohort_id,))
            remaining = cur.fetchone()

    print(f"cohort_id={cohort_id}")
    print(f"sessions_updated={sessions_updated}")
    print(f"regimes_updated={regimes_updated}")
    print(f"session_missing={remaining['session_missing']}")
    print(f"regime_missing={remaining['regime_missing']}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("broker_orders=0")
    print("VERDICT=FORWARD_EDGE_CONTEXT_BACKFILL_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
