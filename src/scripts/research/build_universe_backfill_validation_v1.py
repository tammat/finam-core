#!/usr/bin/env python3

import os
import psycopg2


SOURCE = "universe_backfill_v1"

TARGETS = [
    ("BRENT", "BR%@RTSX"),
    ("NATURAL_GAS", "NG%@RTSX"),
    ("USD_RUB", "USDRUBF@RTSX"),
    ("SBER", "SBER@MISX"),
    ("LKOH", "LKOH@MISX"),
    ("PLZL", "PLZL@MISX"),
]


def fetch_one(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchone()


def main() -> int:
    print("=== UNIVERSE_BACKFILL_VALIDATION_V1 ===")
    print("mode=validation_read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    db = os.environ.get("DATABASE_URL", "")
    if not db:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2
    if db.startswith("sqlite"):
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    failures = 0

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            print("")
            print("TARGET_VALIDATION")

            for name, pattern in TARGETS:
                op = "LIKE" if "%" in pattern else "="

                feature_rows, first_feature, last_feature = fetch_one(
                    cur,
                    f"""
                    SELECT COUNT(*), MIN(ts), MAX(ts)
                    FROM public.feature_snapshots
                    WHERE symbol {op} %s
                      AND ts IS NOT NULL
                      AND close IS NOT NULL;
                    """,
                    (pattern,),
                )

                snapshot_rows, first_snapshot, last_snapshot = fetch_one(
                    cur,
                    f"""
                    SELECT COUNT(*), MIN(snapshot_ts), MAX(snapshot_ts)
                    FROM research.market_state_snapshots_v1
                    WHERE symbol {op} %s
                      AND source=%s;
                    """,
                    (pattern, SOURCE),
                )

                status = "OK"
                if int(feature_rows) > 0 and int(snapshot_rows) == 0:
                    status = "FAILED_NO_SNAPSHOTS"
                    failures += 1
                elif int(snapshot_rows) < int(feature_rows):
                    status = "PARTIAL_COVERAGE"
                elif int(snapshot_rows) >= int(feature_rows):
                    status = "OK"

                print(
                    "TARGET "
                    f"name={name} pattern={pattern} "
                    f"feature_rows={feature_rows} "
                    f"snapshot_rows={snapshot_rows} "
                    f"first_feature={first_feature} "
                    f"last_feature={last_feature} "
                    f"first_snapshot={first_snapshot} "
                    f"last_snapshot={last_snapshot} "
                    f"status={status}"
                )

            total_snapshots, first_ts, last_ts = fetch_one(
                cur,
                """
                SELECT COUNT(*), MIN(snapshot_ts), MAX(snapshot_ts)
                FROM research.market_state_snapshots_v1
                WHERE source=%s;
                """,
                (SOURCE,),
            )

            duplicates = fetch_one(
                cur,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT snapshot_ts, symbol, timeframe, compact_signature, COUNT(*)
                    FROM research.market_state_snapshots_v1
                    WHERE source=%s
                    GROUP BY snapshot_ts, symbol, timeframe, compact_signature
                    HAVING COUNT(*) > 1
                ) q;
                """,
                (SOURCE,),
            )[0]

    print("")
    print("SUMMARY")
    print(f"source={SOURCE}")
    print(f"snapshots_total={total_snapshots}")
    print(f"first_snapshot={first_ts}")
    print(f"last_snapshot={last_ts}")
    print(f"duplicates={duplicates}")
    print(f"failures={failures}")

    verdict = "UNIVERSE_BACKFILL_VALIDATION_OK"
    if duplicates:
        verdict = "UNIVERSE_BACKFILL_VALIDATION_DUPLICATES"
    elif failures:
        verdict = "UNIVERSE_BACKFILL_VALIDATION_FAILED"

    print("")
    print(f"VERDICT={verdict}")
    return 0 if verdict == "UNIVERSE_BACKFILL_VALIDATION_OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
