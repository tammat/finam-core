#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


TRUSTED_FROM = {
    "BR": "2026-06-05 00:00:00+00",
    "NG": "2026-06-03 00:00:00+00",
}


def pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return part * 100.0 / total


def main() -> None:
    print("=== EXIT REASON TRUSTED COVERAGE REPORT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("policy=exit_reason_trusted_window_policy_v1")
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
                        coalesce(exit_ts, closed_at, created_at) AS ts,
                        nullif(payload->>'exit_reason', '') AS exit_reason
                    FROM closed_trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                ),
                marked AS (
                    SELECT
                        *,
                        CASE
                            WHEN root='BR' AND ts >= timestamptz '2026-06-05 00:00:00+00' THEN true
                            WHEN root='NG' AND ts >= timestamptz '2026-06-03 00:00:00+00' THEN true
                            ELSE false
                        END AS trusted
                    FROM base
                )
                SELECT
                    root,
                    trusted,
                    count(*) AS total,
                    count(*) FILTER (WHERE exit_reason IS NOT NULL) AS matched,
                    count(*) FILTER (WHERE exit_reason IS NULL) AS unmatched
                FROM marked
                GROUP BY root, trusted
                ORDER BY root, trusted DESC
            """)
            rows = cur.fetchall()

            print("TRUSTED_ROOT_COVERAGE")
            for r in rows:
                total = int(r["total"] or 0)
                matched = int(r["matched"] or 0)
                unmatched = int(r["unmatched"] or 0)
                trusted = bool(r["trusted"])
                print(
                    f"ROOT_ROW root={r['root']} trusted={int(trusted)} "
                    f"total={total} matched={matched} unmatched={unmatched} "
                    f"coverage_pct={pct(matched, total):.2f}"
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
                        coalesce(exit_ts, closed_at, created_at) AS ts,
                        nullif(payload->>'exit_reason', '') AS exit_reason
                    FROM closed_trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                ),
                marked AS (
                    SELECT
                        *,
                        CASE
                            WHEN root='BR' AND ts >= timestamptz '2026-06-05 00:00:00+00' THEN true
                            WHEN root='NG' AND ts >= timestamptz '2026-06-03 00:00:00+00' THEN true
                            ELSE false
                        END AS trusted
                    FROM base
                )
                SELECT
                    root,
                    symbol,
                    trusted,
                    count(*) AS total,
                    count(*) FILTER (WHERE exit_reason IS NOT NULL) AS matched,
                    count(*) FILTER (WHERE exit_reason IS NULL) AS unmatched
                FROM marked
                GROUP BY root, symbol, trusted
                ORDER BY root, symbol, trusted DESC
            """)
            symbol_rows = cur.fetchall()

            print("TRUSTED_SYMBOL_COVERAGE")
            for r in symbol_rows:
                total = int(r["total"] or 0)
                matched = int(r["matched"] or 0)
                unmatched = int(r["unmatched"] or 0)
                trusted = bool(r["trusted"])
                print(
                    f"SYMBOL_ROW root={r['root']} symbol={r['symbol']} trusted={int(trusted)} "
                    f"total={total} matched={matched} unmatched={unmatched} "
                    f"coverage_pct={pct(matched, total):.2f}"
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
                        coalesce(exit_ts, closed_at, created_at) AS ts,
                        coalesce(nullif(payload->>'exit_reason', ''), 'NO_MATCH') AS exit_reason
                    FROM closed_trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                ),
                marked AS (
                    SELECT
                        *,
                        CASE
                            WHEN root='BR' AND ts >= timestamptz '2026-06-05 00:00:00+00' THEN true
                            WHEN root='NG' AND ts >= timestamptz '2026-06-03 00:00:00+00' THEN true
                            ELSE false
                        END AS trusted
                    FROM base
                )
                SELECT
                    root,
                    trusted,
                    exit_reason,
                    count(*) AS rows
                FROM marked
                GROUP BY root, trusted, exit_reason
                ORDER BY root, trusted DESC, rows DESC, exit_reason
            """)
            reason_rows = cur.fetchall()

            print("TRUSTED_EXIT_REASON_DISTRIBUTION")
            for r in reason_rows:
                print(
                    f"REASON_ROW root={r['root']} trusted={int(bool(r['trusted']))} "
                    f"exit_reason={r['exit_reason']} rows={r['rows']}"
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
                        coalesce(exit_ts, closed_at, created_at) AS ts,
                        net_pnl,
                        coalesce(nullif(payload->>'exit_reason', ''), 'NO_MATCH') AS exit_reason
                    FROM closed_trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                ),
                marked AS (
                    SELECT
                        *,
                        CASE
                            WHEN root='BR' AND ts >= timestamptz '2026-06-05 00:00:00+00' THEN true
                            WHEN root='NG' AND ts >= timestamptz '2026-06-03 00:00:00+00' THEN true
                            ELSE false
                        END AS trusted
                    FROM base
                )
                SELECT
                    root,
                    exit_reason,
                    count(*) AS trades,
                    count(*) FILTER (WHERE net_pnl > 0) AS wins,
                    count(*) FILTER (WHERE net_pnl < 0) AS losses,
                    sum(net_pnl) AS net_pnl,
                    avg(net_pnl) AS expectancy
                FROM marked
                WHERE trusted = true
                GROUP BY root, exit_reason
                ORDER BY root, trades DESC, exit_reason
            """)
            quality_rows = cur.fetchall()

            print("TRUSTED_EXIT_REASON_QUALITY")
            for r in quality_rows:
                print(
                    f"QUALITY_ROW root={r['root']} exit_reason={r['exit_reason']} "
                    f"trades={r['trades']} wins={r['wins']} losses={r['losses']} "
                    f"net_pnl={float(r['net_pnl'] or 0):.6f} "
                    f"expectancy={float(r['expectancy'] or 0):.6f}"
                )
            print()

    trusted_total = sum(int(r["total"] or 0) for r in rows if bool(r["trusted"]))
    trusted_matched = sum(int(r["matched"] or 0) for r in rows if bool(r["trusted"]))
    trusted_coverage = pct(trusted_matched, trusted_total)

    if trusted_total == 0:
        verdict = "NO_TRUSTED_ROWS"
    elif trusted_coverage >= 80:
        verdict = "TRUSTED_COVERAGE_OK"
    else:
        verdict = "TRUSTED_COVERAGE_INCOMPLETE"

    print("SUMMARY")
    print(f"BR_TRUSTED_FROM={TRUSTED_FROM['BR']}")
    print(f"NG_TRUSTED_FROM={TRUSTED_FROM['NG']}")
    print(f"TRUSTED_TOTAL_ROWS={trusted_total}")
    print(f"TRUSTED_MATCHED_ROWS={trusted_matched}")
    print(f"TRUSTED_COVERAGE_PCT={trusted_coverage:.2f}")
    print(f"VERDICT={verdict}")
    print("EXIT_REASON_TRUSTED_COVERAGE_REPORT_V1_OK")


if __name__ == "__main__":
    main()
