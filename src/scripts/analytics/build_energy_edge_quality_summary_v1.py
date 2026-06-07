#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


def db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL_NOT_SET")
    return url


def fetch(cur, sql: str, params=None):
    cur.execute(sql, params or ())
    return cur.fetchall()


def main() -> None:
    print("=== ENERGY EDGE QUALITY SUMMARY V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("scope=NG_BR_EDGE_QUALITY")
    print()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:

            print("TRADE_SUMMARY_BY_ROOT_SIDE")
            rows = fetch(cur, """
                WITH base AS (
                    SELECT
                        CASE
                            WHEN left(symbol, 2) = 'BR' THEN 'BR'
                            WHEN left(symbol, 2) = 'NG' THEN 'NG'
                            ELSE 'OTHER'
                        END AS root,
                        symbol,
                        upper(side) AS side,
                        count(*) AS rows,
                        max(ts) AS last_ts
                    FROM trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                      AND coalesce(is_invalid,false)=false
                    GROUP BY 1,2,3
                )
                SELECT * FROM base
                ORDER BY root, symbol, side;
            """)
            for r in rows:
                print(
                    f"TRADE_ROW root={r['root']} symbol={r['symbol']} "
                    f"side={r['side']} rows={r['rows']} last_ts={r['last_ts']}"
                )
            print()

            print("CLOSED_TRADE_QUALITY_BY_ROOT_SIDE")
            rows = fetch(cur, """
                WITH base AS (
                    SELECT
                        CASE
                            WHEN left(symbol, 2) = 'BR' THEN 'BR'
                            WHEN left(symbol, 2) = 'NG' THEN 'NG'
                            ELSE 'OTHER'
                        END AS root,
                        symbol,
                        upper(coalesce(side, 'UNKNOWN')) AS side,
                        coalesce(net_pnl, 0)::numeric AS pnl
                    FROM closed_trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                )
                SELECT
                    root,
                    symbol,
                    side,
                    count(*) AS trades,
                    count(*) FILTER (WHERE pnl > 0) AS wins,
                    count(*) FILTER (WHERE pnl < 0) AS losses,
                    round(sum(pnl), 6) AS net_pnl,
                    round(avg(pnl), 6) AS expectancy,
                    CASE
                        WHEN abs(sum(pnl) FILTER (WHERE pnl < 0)) > 0
                        THEN round(
                            (sum(pnl) FILTER (WHERE pnl > 0))
                            / abs(sum(pnl) FILTER (WHERE pnl < 0)),
                            6
                        )
                        ELSE NULL
                    END AS profit_factor
                FROM base
                GROUP BY root, symbol, side
                ORDER BY root, symbol, side;
            """)
            if rows:
                for r in rows:
                    print(
                        f"QUALITY_ROW root={r['root']} symbol={r['symbol']} side={r['side']} "
                        f"trades={r['trades']} wins={r['wins']} losses={r['losses']} "
                        f"net_pnl={r['net_pnl']} expectancy={r['expectancy']} "
                        f"profit_factor={r['profit_factor']}"
                    )
            else:
                print("NO_CLOSED_TRADES_ROWS")
            print()

            print("EXIT_REASON_SUMMARY")
            rows = fetch(cur, """
                SELECT
                    CASE
                        WHEN left(symbol, 2) = 'BR' THEN 'BR'
                        WHEN left(symbol, 2) = 'NG' THEN 'NG'
                        ELSE 'OTHER'
                    END AS root,
                    symbol,
                    coalesce(
                        payload->>'reason',
                        payload->'features'->>'reason',
                        payload->>'exit_reason',
                        'UNKNOWN'
                    ) AS reason,
                    count(*) AS rows,
                    max(ts) AS last_ts
                FROM trades
                WHERE left(symbol, 2) IN ('BR','NG')
                  AND coalesce(is_invalid,false)=false
                  AND upper(side) IN ('BUY','SELL')
                GROUP BY 1,2,3
                ORDER BY root, symbol, rows DESC;
            """)
            for r in rows:
                print(
                    f"EXIT_REASON_ROW root={r['root']} symbol={r['symbol']} "
                    f"reason={str(r['reason']).replace(' ', '_')} rows={r['rows']} last_ts={r['last_ts']}"
                )
            print()

            print("POLICY_STATUS")
            print("POLICY_ROW root=BR long_policy=SHADOW_OR_BLOCKED short_policy=SHADOW_FOR_CANONICAL_SELL live_status=WAIT_NEW_SELL_AFTER_FIX")
            print("POLICY_ROW root=NG long_policy=ALLOWED short_policy=BLOCKED_AFTER_NEGATIVE_EDGE live_status=ACTIVE")
            print()

            print("DECISION_SUMMARY")
            print("BR_LONG=WEAK_OR_BLOCKED")
            print("BR_SHORT=POSITIVE_RESEARCH_SHADOW_ROUTE_FIXED_WAIT_LIVE_CONFIRMATION")
            print("NG_LONG=ALLOWED")
            print("NG_SHORT=BLOCKED_NEGATIVE_EDGE")
            print()

            print("VERDICT=ENERGY_EDGE_QUALITY_SUMMARY_RECORDED")
            print("ENERGY_EDGE_QUALITY_SUMMARY_V1_OK")


if __name__ == "__main__":
    main()
