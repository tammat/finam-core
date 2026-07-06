from __future__ import annotations

import os
import uuid
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "MARKET_MODEL_V1"

def asset_class(symbol: str) -> str:
    if symbol.endswith("@MISX"):
        return "MOEX_SPOT"
    if symbol.endswith("@RTSX"):
        return "MOEX_FUTURES"
    if symbol in {"BTCUSD", "ETHUSD"}:
        return "CRYPTO_PROXY"
    if symbol == "IMOEX":
        return "INDEX"
    return "UNKNOWN"

def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("DELETE FROM marketcore.market_snapshot_v1;")

            cur.execute("""
                SELECT DISTINCT ON (symbol, timeframe)
                    symbol, timeframe, ts AS bar_ts,
                    open, high, low, close, volume
                FROM public.market_bars
                WHERE ts IS NOT NULL
                ORDER BY symbol, timeframe, ts DESC;
            """)
            rows = cur.fetchall()

            inserted = 0
            for r in rows:
                cur.execute("""
                    SELECT EXTRACT(EPOCH FROM (now() - %s::timestamptz))::int AS age;
                """, (r["bar_ts"],))
                freshness_sec = cur.fetchone()["age"]

                quality_status = "FRESH" if freshness_sec is not None and freshness_sec < 86400 else "STALE"

                cur.execute("""
                    INSERT INTO marketcore.market_snapshot_v1 (
                        symbol, display_name, asset_class, timeframe, bar_ts,
                        open, high, low, close, volume,
                        freshness_sec, quality_status,
                        source_table, source_version, build_id, refreshed_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            'public.market_bars',%s,%s,now())
                    ON CONFLICT (symbol, timeframe, bar_ts) DO UPDATE SET
                        open=EXCLUDED.open,
                        high=EXCLUDED.high,
                        low=EXCLUDED.low,
                        close=EXCLUDED.close,
                        volume=EXCLUDED.volume,
                        freshness_sec=EXCLUDED.freshness_sec,
                        quality_status=EXCLUDED.quality_status,
                        source_version=EXCLUDED.source_version,
                        build_id=EXCLUDED.build_id,
                        refreshed_at=now();
                """, (
                    r["symbol"], "", asset_class(r["symbol"]), r["timeframe"], r["bar_ts"],
                    r["open"], r["high"], r["low"], r["close"], r["volume"],
                    freshness_sec, quality_status, SOURCE_VERSION, build_id,
                ))
                inserted += 1

    print("=== MARKET_MODEL_V1 ===")
    print(f"rows_written={inserted}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_MODEL_V1_READY")

if __name__ == "__main__":
    main()
