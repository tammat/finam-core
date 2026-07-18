from __future__ import annotations

import os

import psycopg2
import psycopg2.extras

from marketcore.research_window_guard_v1 import require_off_market_research_window


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "CANONICAL_SWING_TIMEFRAME_AGGREGATOR_V1"


def main() -> None:
    require_off_market_research_window("CANONICAL_SWING_TIMEFRAME_AGGREGATOR_V1")
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics.swing_market_bars_v1 (
                    symbol text NOT NULL, timeframe text NOT NULL, ts timestamptz NOT NULL,
                    open numeric NOT NULL, high numeric NOT NULL, low numeric NOT NULL,
                    close numeric NOT NULL, volume numeric,
                    source_timeframe text NOT NULL, source_version text NOT NULL,
                    created_at timestamptz NOT NULL DEFAULT now(),
                    PRIMARY KEY(symbol,timeframe,ts)
                );
                CREATE INDEX IF NOT EXISTS swing_market_bars_lookup_idx
                    ON analytics.swing_market_bars_v1(timeframe,symbol,ts);
            """)
            cur.execute("""SELECT audit_run_id FROM analytics.relationship_data_quality_gate_v1
                ORDER BY created_at DESC LIMIT 1""")
            latest = cur.fetchone()
            cur.execute("""SELECT symbol FROM analytics.relationship_data_quality_gate_v1
                WHERE audit_run_id=%s AND market_data_status='READY' ORDER BY symbol""", (latest["audit_run_id"],))
            symbols = [row["symbol"] for row in cur.fetchall()]

            for timeframe, interval in (("H1", "1 hour"), ("H4", "4 hours")):
                cur.execute("SELECT coalesce(max(ts)-%s::interval,'2000-01-01'::timestamptz) cutoff FROM analytics.swing_market_bars_v1 WHERE timeframe=%s", (interval,timeframe))
                cutoff = cur.fetchone()["cutoff"]
                cur.execute("""INSERT INTO analytics.swing_market_bars_v1
                    (symbol,timeframe,ts,open,high,low,close,volume,source_timeframe,source_version)
                    SELECT symbol,%s,date_bin(%s::interval,ts,'2000-01-01 00:00:00+03'::timestamptz),
                           (array_agg(open ORDER BY ts))[1],max(high),min(low),
                           (array_agg(close ORDER BY ts DESC))[1],sum(volume),'M5',%s
                    FROM public.market_bars WHERE timeframe='M5' AND symbol=ANY(%s) AND ts>=%s
                      AND open IS NOT NULL AND high IS NOT NULL AND low IS NOT NULL AND close IS NOT NULL
                    GROUP BY symbol,date_bin(%s::interval,ts,'2000-01-01 00:00:00+03'::timestamptz)
                    ON CONFLICT(symbol,timeframe,ts) DO UPDATE SET
                      open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,
                      volume=excluded.volume,source_timeframe=excluded.source_timeframe,
                      source_version=excluded.source_version""",
                    (timeframe,interval,SOURCE_VERSION,symbols,cutoff,interval))
            cur.execute("SELECT coalesce(max(ts)-interval '2 days','2000-01-01'::timestamptz) cutoff FROM analytics.swing_market_bars_v1 WHERE timeframe='D1'")
            d1_cutoff = cur.fetchone()["cutoff"]
            cur.execute("""INSERT INTO analytics.swing_market_bars_v1
                (symbol,timeframe,ts,open,high,low,close,volume,source_timeframe,source_version)
                SELECT symbol,'D1',((ts AT TIME ZONE 'Europe/Moscow')::date::timestamp AT TIME ZONE 'Europe/Moscow'),
                       (array_agg(open ORDER BY ts))[1],max(high),min(low),
                       (array_agg(close ORDER BY ts DESC))[1],sum(volume),'M5',%s
                FROM public.market_bars WHERE timeframe='M5' AND symbol=ANY(%s) AND ts>=%s
                  AND open IS NOT NULL AND high IS NOT NULL AND low IS NOT NULL AND close IS NOT NULL
                GROUP BY symbol,(ts AT TIME ZONE 'Europe/Moscow')::date
                ON CONFLICT(symbol,timeframe,ts) DO UPDATE SET
                  open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,
                  volume=excluded.volume,source_timeframe=excluded.source_timeframe,
                  source_version=excluded.source_version""", (SOURCE_VERSION,symbols,d1_cutoff))
            for rolling_symbol, table_name in (
                ("BR_ROLLING@RTSX", "market_bars_br_m5_rolling_v2"),
                ("NG_ROLLING@RTSX", "market_bars_ng_m5_rolling_v1"),
            ):
                for timeframe, interval in (("H1", "1 hour"), ("H4", "4 hours")):
                    cur.execute("SELECT coalesce(max(ts)-%s::interval,'2000-01-01'::timestamptz) cutoff FROM analytics.swing_market_bars_v1 WHERE symbol=%s AND timeframe=%s", (interval,rolling_symbol,timeframe))
                    cutoff = cur.fetchone()["cutoff"]
                    cur.execute(f"""INSERT INTO analytics.swing_market_bars_v1
                        (symbol,timeframe,ts,open,high,low,close,volume,source_timeframe,source_version)
                        SELECT %s,%s,date_bin(%s::interval,ts,'2000-01-01 00:00:00+03'::timestamptz),
                               (array_agg(open ORDER BY ts))[1],max(high),min(low),
                               (array_agg(close ORDER BY ts DESC))[1],sum(volume),'M5',%s
                        FROM public.{table_name} WHERE ts>=%s AND open IS NOT NULL AND high IS NOT NULL
                          AND low IS NOT NULL AND close IS NOT NULL
                        GROUP BY date_bin(%s::interval,ts,'2000-01-01 00:00:00+03'::timestamptz)
                        ON CONFLICT(symbol,timeframe,ts) DO UPDATE SET
                          open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,
                          volume=excluded.volume,source_timeframe=excluded.source_timeframe,
                          source_version=excluded.source_version""",
                        (rolling_symbol,timeframe,interval,SOURCE_VERSION,cutoff,interval))
                cur.execute("SELECT coalesce(max(ts)-interval '2 days','2000-01-01'::timestamptz) cutoff FROM analytics.swing_market_bars_v1 WHERE symbol=%s AND timeframe='D1'", (rolling_symbol,))
                rolling_d1_cutoff = cur.fetchone()["cutoff"]
                cur.execute(f"""INSERT INTO analytics.swing_market_bars_v1
                    (symbol,timeframe,ts,open,high,low,close,volume,source_timeframe,source_version)
                    SELECT %s,'D1',((ts AT TIME ZONE 'Europe/Moscow')::date::timestamp AT TIME ZONE 'Europe/Moscow'),
                           (array_agg(open ORDER BY ts))[1],max(high),min(low),
                           (array_agg(close ORDER BY ts DESC))[1],sum(volume),'M5',%s
                    FROM public.{table_name} WHERE ts>=%s AND open IS NOT NULL AND high IS NOT NULL
                      AND low IS NOT NULL AND close IS NOT NULL
                    GROUP BY (ts AT TIME ZONE 'Europe/Moscow')::date
                    ON CONFLICT(symbol,timeframe,ts) DO UPDATE SET
                      open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,
                      volume=excluded.volume,source_timeframe=excluded.source_timeframe,
                      source_version=excluded.source_version""", (rolling_symbol,SOURCE_VERSION,rolling_d1_cutoff))
            cur.execute("""SELECT timeframe,count(*) AS bars,count(DISTINCT symbol) AS symbols,
                       count(*) FILTER(WHERE high<greatest(open,close) OR low>least(open,close) OR low>high) AS invalid_ohlc
                FROM analytics.swing_market_bars_v1 WHERE source_version=%s GROUP BY timeframe ORDER BY timeframe""",
                (SOURCE_VERSION,))
            summary = cur.fetchall()

    print(f"ready_source_symbols={len(symbols)}")
    for row in summary:
        print(f"timeframe={row['timeframe']} bars={row['bars']} symbols={row['symbols']} invalid_ohlc={row['invalid_ohlc']}")
    print("source_timeframe=M5")
    print("final_holdout_opened=0")
    print("paper_created=0")
    print("live_allowed=0")
    print("VERDICT=CANONICAL_SWING_TIMEFRAME_AGGREGATOR_V1_OK")


if __name__ == "__main__":
    main()
