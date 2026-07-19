from __future__ import annotations

import os

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
LOCK_ID = 941903131


DETECT_SQL = """
WITH fill_base AS (
    SELECT
        f.fill_id,f.symbol,upper(f.side) AS side,f.ts,
        date_trunc('hour',f.ts) AS hour_start,
        EXISTS(SELECT 1 FROM public.signal_fills sf WHERE sf.fill_id=f.fill_id) AS linked
    FROM public.fills f
    WHERE f.ts >= clock_timestamp()-(%s * interval '1 day')
), hourly AS (
    SELECT
        symbol,side,hour_start,min(ts) AS range_start,max(ts) AS range_end,
        count(*)::integer AS fill_count,
        count(*) FILTER(WHERE linked)::integer AS linked_count
    FROM fill_base
    GROUP BY symbol,side,hour_start
), anomaly AS (
    SELECT h.*
    FROM hourly h
    WHERE h.fill_count >= %s
      AND h.linked_count = 0
      AND NOT EXISTS (
          SELECT 1 FROM hourly opposite
          WHERE opposite.symbol=h.symbol
            AND opposite.hour_start=h.hour_start
            AND opposite.side<>h.side
            AND opposite.fill_count >= greatest(1,h.fill_count/10)
      )
)
INSERT INTO analytics.paper_fill_anomaly_quarantine_v1(
    anomaly_key,symbol,side,range_start,range_end,fill_count,reason_code,
    detection_source,enabled,detected_at,updated_at)
SELECT
    md5(symbol||'|'||side||'|'||hour_start::text),symbol,side,range_start,
    range_end+interval '1 microsecond',fill_count,'ONE_SIDED_UNLINKED_FILL_STORM',
    'PAPER_FILL_ANOMALY_DETECTOR_V1',true,clock_timestamp(),clock_timestamp()
FROM anomaly
ON CONFLICT(anomaly_key) DO UPDATE SET
    range_start=least(analytics.paper_fill_anomaly_quarantine_v1.range_start,excluded.range_start),
    range_end=greatest(analytics.paper_fill_anomaly_quarantine_v1.range_end,excluded.range_end),
    fill_count=greatest(analytics.paper_fill_anomaly_quarantine_v1.fill_count,excluded.fill_count),
    updated_at=clock_timestamp()
RETURNING anomaly_key;
"""


def main() -> int:
    lookback_days = int(os.getenv("PAPER_FILL_ANOMALY_LOOKBACK_DAYS", "7"))
    hourly_threshold = int(os.getenv("PAPER_FILL_ANOMALY_HOURLY_THRESHOLD", "60"))
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_xact_lock(%s) locked", (LOCK_ID,))
            if not cursor.fetchone()["locked"]:
                print("VERDICT=PAPER_FILL_ANOMALY_DETECTOR_ALREADY_RUNNING")
                return 0
            cursor.execute(DETECT_SQL, (lookback_days, hourly_threshold))
            affected = len(cursor.fetchall())
            cursor.execute(
                """SELECT count(*) ranges,coalesce(sum(fill_count),0) fills
                   FROM analytics.paper_fill_anomaly_quarantine_v1 WHERE enabled"""
            )
            totals = cursor.fetchone()
    print(f"ranges_detected_or_updated={affected}")
    print(f"quarantine_ranges={totals['ranges']}")
    print(f"quarantined_fills_estimate={totals['fills']}")
    print("VERDICT=PAPER_FILL_ANOMALY_DETECTOR_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
