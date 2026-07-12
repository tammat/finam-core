from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "SWING_DATA_QUALITY_GATE_V1"
MIN_BARS = {"H1": 1500, "H4": 400, "D1": 250}


def main() -> None:
    audit_run_id = str(uuid.uuid4())
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics.swing_data_quality_gate_v1 (
                    audit_run_id uuid NOT NULL, symbol text NOT NULL, timeframe text NOT NULL,
                    bars integer NOT NULL, trading_days integer NOT NULL,
                    first_ts timestamptz, last_ts timestamptz,
                    duplicate_rows integer NOT NULL, invalid_ohlc_rows integer NOT NULL,
                    quality_status text NOT NULL, reason_codes jsonb NOT NULL,
                    source_version text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
                    PRIMARY KEY(audit_run_id,symbol,timeframe)
                );
            """)
            cur.execute("""SELECT symbol,timeframe,count(*) AS bars,count(DISTINCT (ts AT TIME ZONE 'Europe/Moscow')::date) AS days,
                       min(ts) AS first_ts,max(ts) AS last_ts,
                       count(*)-count(DISTINCT ts) AS duplicates,
                       count(*) FILTER(WHERE high<greatest(open,close) OR low>least(open,close) OR low>high OR open<=0 OR close<=0) AS invalid
                FROM analytics.swing_market_bars_v1 GROUP BY symbol,timeframe ORDER BY symbol,timeframe""")
            rows = cur.fetchall()
            ready = blocked = 0
            for row in rows:
                reasons = []
                if int(row["bars"]) < MIN_BARS[row["timeframe"]]:
                    reasons.append("INSUFFICIENT_HISTORY")
                if int(row["duplicates"]):
                    reasons.append("DUPLICATE_TIMESTAMPS")
                if int(row["invalid"]):
                    reasons.append("INVALID_OHLC")
                status = "READY" if not reasons else "BLOCKED"
                ready += int(status == "READY")
                blocked += int(status == "BLOCKED")
                cur.execute("""INSERT INTO analytics.swing_data_quality_gate_v1
                    (audit_run_id,symbol,timeframe,bars,trading_days,first_ts,last_ts,duplicate_rows,
                     invalid_ohlc_rows,quality_status,reason_codes,source_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (audit_run_id,row["symbol"],row["timeframe"],row["bars"],row["days"],row["first_ts"],row["last_ts"],
                     row["duplicates"],row["invalid"],status,psycopg2.extras.Json(reasons),SOURCE_VERSION))

    print(f"audit_run_id={audit_run_id}")
    print(f"rows={len(rows)}")
    print(f"ready={ready}")
    print(f"blocked={blocked}")
    print("swing_factory_allowed=" + ("1" if blocked == 0 else "0"))
    print("final_holdout_opened=0")
    print("live_allowed=0")
    print("VERDICT=SWING_DATA_QUALITY_GATE_V1_OK")


if __name__ == "__main__":
    main()
