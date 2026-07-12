from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(os.getenv("RELATIONSHIP_DATA_QUALITY_CONFIG", ROOT / "config/research/relationship_data_quality_v1.json"))
SOURCE_VERSION = "RELATIONSHIP_DATA_QUALITY_GATE_V1"


def source_sql(symbol: str) -> tuple[str, tuple]:
    if symbol == "BR_ROLLING@RTSX":
        return "SELECT ts,open,high,low,close FROM public.market_bars_br_m5_rolling_v2", ()
    return "SELECT ts,open,high,low,close FROM public.market_bars WHERE symbol=%s AND timeframe=%s", (symbol, "M5")


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    run_id = uuid.uuid4()
    ready = blocked = 0
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for symbol in config["symbols"]:
                query, params = source_sql(symbol)
                cur.execute(f"""WITH src AS ({query})
                    SELECT count(*) AS bars,count(DISTINCT (ts AT TIME ZONE 'Europe/Moscow')::date) AS trading_days,
                           min(ts) AS first_ts,max(ts) AS last_ts,
                           extract(epoch FROM (now()-max(ts)))/3600.0 AS age_hours,
                           count(*)-count(DISTINCT ts) AS duplicates,
                           count(*) FILTER(WHERE close IS NULL OR close<=0 OR high<low OR high<greatest(open,close) OR low>least(open,close)) AS invalid
                    FROM src""", params)
                quality = dict(cur.fetchone())
                cur.execute(f"""WITH src AS ({query})
                    SELECT count(DISTINCT src.ts) AS covered FROM src
                    JOIN analytics_regime_snapshots_v2 regime ON regime.symbol=%s AND regime.timeframe=%s
                     AND regime.ts=src.ts AND regime.confidence>=0.60""", params + (symbol, config["timeframe"]))
                regime_rows = int(cur.fetchone()["covered"] or 0)
                bars = int(quality["bars"] or 0)
                coverage = regime_rows / bars if bars else 0.0
                reasons = []
                if bars < config["minimum_bars"]:
                    reasons.append("INSUFFICIENT_BARS")
                if int(quality["trading_days"] or 0) < config["minimum_trading_days"]:
                    reasons.append("INSUFFICIENT_TRADING_DAYS")
                if quality["age_hours"] is None or float(quality["age_hours"]) > config["maximum_latest_age_hours"]:
                    reasons.append("STALE_DATA")
                if int(quality["duplicates"] or 0) > 0:
                    reasons.append("DUPLICATE_TIMESTAMPS")
                if int(quality["invalid"] or 0) > 0:
                    reasons.append("INVALID_OHLC")
                market_status = "READY" if not reasons else ("DEGRADED" if bars > 0 else "BLOCKED")
                factory_reasons = list(reasons)
                if coverage < config["minimum_regime_coverage"]:
                    factory_reasons.append("INSUFFICIENT_REGIME_COVERAGE")
                factory_status = "READY" if not factory_reasons else "BLOCKED"
                cur.execute("""INSERT INTO analytics.relationship_data_quality_gate_v1
                    (audit_run_id,symbol,timeframe,bars,trading_days,first_ts,last_ts,latest_age_hours,duplicate_rows,
                     invalid_ohlc_rows,regime_rows,regime_coverage_ratio,calendar_gap_status,market_data_status,
                     factory_status,reason_codes,source_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'UNVERIFIED',%s,%s,%s,%s)""",
                    (str(run_id),symbol,config["timeframe"],bars,int(quality["trading_days"] or 0),quality["first_ts"],quality["last_ts"],
                     quality["age_hours"],int(quality["duplicates"] or 0),int(quality["invalid"] or 0),regime_rows,coverage,
                     market_status,factory_status,psycopg2.extras.Json(factory_reasons),SOURCE_VERSION))
                ready += int(factory_status == "READY")
                blocked += int(factory_status == "BLOCKED")
                print(f"symbol={symbol} bars={bars} days={quality['trading_days']} regime_coverage={coverage:.3f} market={market_status} factory={factory_status}")
    print(f"audit_run_id={run_id}")
    print(f"factory_ready={ready}")
    print(f"factory_blocked={blocked}")
    print("calendar_gap_status=UNVERIFIED")
    print("VERDICT=RELATIONSHIP_DATA_QUALITY_GATE_V1_OK")


if __name__ == "__main__":
    main()
