#!/usr/bin/env python3
import os
import sys
import psycopg2

SOURCE = "universe_backfill_v1"

TARGETS = [
    ("BRENT", "BR%@RTSX", "FUTURES"),
    ("NATURAL_GAS", "NG%@RTSX", "FUTURES"),
    ("USD_RUB", "USDRUBF@RTSX", "FUTURES"),
    ("SBER", "SBER@MISX", "EQUITY"),
    ("LKOH", "LKOH@MISX", "EQUITY"),
    ("PLZL", "PLZL@MISX", "EQUITY"),
]

def arg_limit():
    if "--full" in sys.argv:
        return None
    if "--limit" in sys.argv:
        return int(sys.argv[sys.argv.index("--limit") + 1])
    return 50

def main():
    print("=== UNIVERSE_BACKFILL_IMPLEMENTATION_V1 ===", flush=True)
    print("mode=backfill_apply", flush=True)
    print("runtime_changed=0", flush=True)
    print("execution_changed=0", flush=True)
    print("real_trading_enabled=0", flush=True)
    print("orders_sent=0", flush=True)

    db = os.environ.get("DATABASE_URL", "")
    if not db:
        print("db_update=0")
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2
    if db.startswith("sqlite"):
        print("db_update=0")
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    limit = arg_limit()
    total = 0

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            print("")
            print("BACKFILL_TARGETS", flush=True)

            for name, pattern, asset_class in TARGETS:
                op = "LIKE" if "%" in pattern else "="
                limit_sql = "" if limit is None else f"LIMIT {limit}"

                cur.execute(f"""
                    SELECT symbol, timeframe, ts, close,
                           trend_state, volatility_state, session_state
                    FROM public.feature_snapshots
                    WHERE symbol {op} %s
                      AND ts IS NOT NULL
                      AND close IS NOT NULL
                    ORDER BY symbol, timeframe, ts
                    {limit_sql};
                """, (pattern,))

                rows = cur.fetchall()
                total += len(rows)

                for symbol, timeframe, ts, close, trend, vol, session in rows:
                    canonical = (
                        f"TREND={str(trend or 'UNKNOWN').upper()}|"
                        f"VOLATILITY={str(vol or 'UNKNOWN').upper()}|"
                        f"SESSION={str(session or 'UNKNOWN').upper()}"
                    )
                    compact = "MS-" + str(abs(hash(canonical)) % 10**12)

                    cur.execute("""
                        INSERT INTO research.market_state_snapshots_v1 (
                            snapshot_ts, symbol, asset_class, timeframe,
                            canonical_signature, compact_signature,
                            quality, confidence, conflict_score, source
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (snapshot_ts, symbol, timeframe, compact_signature)
                        DO UPDATE SET
                            quality=EXCLUDED.quality,
                            confidence=EXCLUDED.confidence,
                            conflict_score=EXCLUDED.conflict_score,
                            source=EXCLUDED.source;
                    """, (
                        ts, symbol, asset_class, timeframe,
                        canonical, compact,
                        "GOOD", 1.0, 0.0, SOURCE
                    ))

                print(
                    f"TARGET name={name} pattern={pattern} "
                    f"asset_class={asset_class} rows_loaded={len(rows)}",
                    flush=True
                )

        conn.commit()

    print("")
    print("SUMMARY")
    print("source=public.feature_snapshots")
    print(f"target_source={SOURCE}")
    print(f"rows_loaded={total}")
    print("db_update=1")
    print("VERDICT=UNIVERSE_BACKFILL_IMPLEMENTATION_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
