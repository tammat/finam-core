#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


def pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return part * 100.0 / total


def main() -> None:
    print("=== EXIT REASON COVERAGE AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cur.execute("""
                WITH base AS (
                    SELECT
                        id,
                        symbol,
                        CASE
                            WHEN left(symbol, 2) = 'BR' THEN 'BR'
                            WHEN left(symbol, 2) = 'NG' THEN 'NG'
                            ELSE 'OTHER'
                        END AS root,
                        source,
                        coalesce(exit_ts, closed_at, created_at) AS ts,
                        nullif(payload->>'exit_reason', '') AS exit_reason
                    FROM closed_trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                )
                SELECT
                    root,
                    count(*) AS total,
                    count(*) FILTER (WHERE exit_reason IS NOT NULL) AS matched,
                    count(*) FILTER (WHERE exit_reason IS NULL) AS unmatched
                FROM base
                GROUP BY root
                ORDER BY root
            """)
            root_rows = cur.fetchall()

            print("ROOT_COVERAGE")
            for r in root_rows:
                total = int(r["total"] or 0)
                matched = int(r["matched"] or 0)
                unmatched = int(r["unmatched"] or 0)
                print(
                    f"ROOT_ROW root={r['root']} total={total} matched={matched} "
                    f"unmatched={unmatched} coverage_pct={pct(matched, total):.2f}"
                )
            print()

            cur.execute("""
                WITH base AS (
                    SELECT
                        source,
                        nullif(payload->>'exit_reason', '') AS exit_reason
                    FROM closed_trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                )
                SELECT
                    source,
                    count(*) AS total,
                    count(*) FILTER (WHERE exit_reason IS NOT NULL) AS matched,
                    count(*) FILTER (WHERE exit_reason IS NULL) AS unmatched
                FROM base
                GROUP BY source
                ORDER BY source
            """)
            source_rows = cur.fetchall()

            print("SOURCE_COVERAGE")
            for r in source_rows:
                total = int(r["total"] or 0)
                matched = int(r["matched"] or 0)
                unmatched = int(r["unmatched"] or 0)
                print(
                    f"SOURCE_ROW source={r['source']} total={total} matched={matched} "
                    f"unmatched={unmatched} coverage_pct={pct(matched, total):.2f}"
                )
            print()

            cur.execute("""
                WITH base AS (
                    SELECT
                        symbol,
                        CASE
                            WHEN left(symbol, 2) = 'BR' THEN 'BR'
                            WHEN left(symbol, 2) = 'NG' THEN 'NG'
                            ELSE 'OTHER'
                        END AS root,
                        nullif(payload->>'exit_reason', '') AS exit_reason
                    FROM closed_trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                )
                SELECT
                    root,
                    symbol,
                    count(*) AS total,
                    count(*) FILTER (WHERE exit_reason IS NOT NULL) AS matched,
                    count(*) FILTER (WHERE exit_reason IS NULL) AS unmatched
                FROM base
                GROUP BY root, symbol
                ORDER BY root, symbol
            """)
            symbol_rows = cur.fetchall()

            print("SYMBOL_COVERAGE")
            for r in symbol_rows:
                total = int(r["total"] or 0)
                matched = int(r["matched"] or 0)
                unmatched = int(r["unmatched"] or 0)
                print(
                    f"SYMBOL_ROW root={r['root']} symbol={r['symbol']} total={total} "
                    f"matched={matched} unmatched={unmatched} coverage_pct={pct(matched, total):.2f}"
                )
            print()

            cur.execute("""
                WITH base AS (
                    SELECT
                        CASE
                            WHEN left(symbol, 2) = 'BR' THEN 'BR'
                            WHEN left(symbol, 2) = 'NG' THEN 'NG'
                            ELSE 'OTHER'
                        END AS root,
                        date_trunc('day', coalesce(exit_ts, closed_at, created_at)) AS day,
                        nullif(payload->>'exit_reason', '') AS exit_reason
                    FROM closed_trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                )
                SELECT
                    root,
                    day,
                    count(*) AS total,
                    count(*) FILTER (WHERE exit_reason IS NOT NULL) AS matched,
                    count(*) FILTER (WHERE exit_reason IS NULL) AS unmatched
                FROM base
                GROUP BY root, day
                ORDER BY root, day
            """)
            day_rows = cur.fetchall()

            print("DAY_COVERAGE")
            for r in day_rows:
                total = int(r["total"] or 0)
                matched = int(r["matched"] or 0)
                unmatched = int(r["unmatched"] or 0)
                day = r["day"].date().isoformat() if r["day"] else "UNKNOWN"
                print(
                    f"DAY_ROW root={r['root']} day={day} total={total} "
                    f"matched={matched} unmatched={unmatched} coverage_pct={pct(matched, total):.2f}"
                )
            print()

            cur.execute("""
                WITH base AS (
                    SELECT
                        CASE
                            WHEN left(symbol, 2) = 'BR' THEN 'BR'
                            WHEN left(symbol, 2) = 'NG' THEN 'NG'
                            ELSE 'OTHER'
                        END AS root,
                        coalesce(nullif(payload->>'exit_reason', ''), 'NO_MATCH') AS exit_reason
                    FROM closed_trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                )
                SELECT
                    root,
                    exit_reason,
                    count(*) AS rows
                FROM base
                GROUP BY root, exit_reason
                ORDER BY root, rows DESC, exit_reason
            """)
            reason_rows = cur.fetchall()

            print("EXIT_REASON_DISTRIBUTION")
            for r in reason_rows:
                print(
                    f"REASON_ROW root={r['root']} exit_reason={r['exit_reason']} rows={r['rows']}"
                )
            print()

    total_all = sum(int(r["total"] or 0) for r in root_rows)
    matched_all = sum(int(r["matched"] or 0) for r in root_rows)
    coverage_all = pct(matched_all, total_all)

    if coverage_all >= 80:
        verdict = "EXIT_REASON_COVERAGE_GOOD"
    elif coverage_all >= 30:
        verdict = "MIXED_COVERAGE_REQUIRES_BACKFILL"
    else:
        verdict = "LOW_COVERAGE_REQUIRES_BACKFILL"

    print("SUMMARY")
    print(f"TOTAL_ROWS={total_all}")
    print(f"MATCHED_ROWS={matched_all}")
    print(f"UNMATCHED_ROWS={total_all - matched_all}")
    print(f"COVERAGE_PCT={coverage_all:.2f}")
    print(f"VERDICT={verdict}")
    print("EXIT_REASON_COVERAGE_AUDIT_V1_OK")


if __name__ == "__main__":
    main()
