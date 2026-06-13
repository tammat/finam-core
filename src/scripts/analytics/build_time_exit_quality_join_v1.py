#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


MAX_JOIN_SECONDS = 180


def db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL_NOT_SET")
    return url


def main() -> None:
    print("=== TIME EXIT QUALITY JOIN V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"join_window_seconds={MAX_JOIN_SECONDS}")
    print()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:

            print("JOINED_EXIT_QUALITY")
            cur.execute(
                """
                WITH exit_events AS (
                    SELECT
                        id AS trade_id,
                        symbol,
                        upper(side) AS exit_side,
                        ts AS exit_event_ts,
                        coalesce(
                            payload->>'reason',
                            payload->'features'->>'reason',
                            payload->>'exit_reason',
                            payload->'features'->>'exit_reason',
                            'UNKNOWN'
                        ) AS exit_reason
                    FROM trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                      AND coalesce(is_invalid,false)=false
                      AND (
                            payload->>'intent_type' = 'EXIT'
                         OR payload->'features'->>'is_exit' = 'True'
                         OR payload->'features'->>'is_exit' = 'true'
                         OR coalesce(payload->>'reason','') IN ('time_exit','stop_loss_long','stop_loss_short','take_profit_long','take_profit_short')
                         OR coalesce(payload->'features'->>'reason','') IN ('time_exit','stop_loss_long','stop_loss_short','take_profit_long','take_profit_short')
                      )
                ),
                joined AS (
                    SELECT
                        ct.id AS closed_trade_id,
                        coalesce(ct.root_symbol,
                            CASE
                                WHEN left(ct.symbol, 2) = 'BR' THEN 'BR'
                                WHEN left(ct.symbol, 2) = 'NG' THEN 'NG'
                                ELSE 'OTHER'
                            END
                        ) AS root,
                        ct.symbol,
                        upper(ct.side) AS closed_side,
                        ct.net_pnl::numeric AS net_pnl,
                        ct.exit_ts,
                        ct.closed_at,
                        ee.exit_reason,
                        ee.exit_event_ts,
                        abs(extract(epoch FROM (
                            coalesce(ct.exit_ts, ct.closed_at, ct.created_at) - ee.exit_event_ts
                        ))) AS join_delta_sec,
                        row_number() OVER (
                            PARTITION BY ct.id
                            ORDER BY abs(extract(epoch FROM (
                                coalesce(ct.exit_ts, ct.closed_at, ct.created_at) - ee.exit_event_ts
                            ))) ASC
                        ) AS rn
                    FROM closed_trades ct
                    LEFT JOIN exit_events ee
                      ON ee.symbol = ct.symbol
                     AND abs(extract(epoch FROM (
                         coalesce(ct.exit_ts, ct.closed_at, ct.created_at) - ee.exit_event_ts
                     ))) <= %s
                    WHERE left(ct.symbol, 2) IN ('BR','NG')
                ),
                best AS (
                    SELECT *
                    FROM joined
                    WHERE rn = 1
                )
                SELECT
                    root,
                    symbol,
                    coalesce(exit_reason, 'NO_MATCH') AS exit_reason,
                    count(*) AS trades,
                    count(*) FILTER (WHERE net_pnl > 0) AS wins,
                    count(*) FILTER (WHERE net_pnl < 0) AS losses,
                    round(sum(net_pnl), 6) AS net_pnl,
                    round(avg(net_pnl), 6) AS expectancy,
                    CASE
                        WHEN abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)) > 0
                        THEN round(
                            (sum(net_pnl) FILTER (WHERE net_pnl > 0))
                            / abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)),
                            6
                        )
                        ELSE NULL
                    END AS profit_factor,
                    round(avg(join_delta_sec)::numeric, 2) AS avg_join_delta_sec
                FROM best
                GROUP BY 1,2,3
                ORDER BY root, symbol, trades DESC, exit_reason;
                """,
                (MAX_JOIN_SECONDS,),
            )

            for r in cur.fetchall():
                print(
                    f"JOIN_ROW root={r['root']} symbol={r['symbol']} "
                    f"exit_reason={str(r['exit_reason']).replace(' ', '_')} "
                    f"trades={r['trades']} wins={r['wins']} losses={r['losses']} "
                    f"net_pnl={r['net_pnl']} expectancy={r['expectancy']} "
                    f"profit_factor={r['profit_factor']} "
                    f"avg_join_delta_sec={r['avg_join_delta_sec']}"
                )
            print()

            print("TIME_EXIT_VS_OTHER")
            cur.execute(
                """
                WITH exit_events AS (
                    SELECT
                        symbol,
                        ts AS exit_event_ts,
                        coalesce(
                            payload->>'reason',
                            payload->'features'->>'reason',
                            payload->>'exit_reason',
                            payload->'features'->>'exit_reason',
                            'UNKNOWN'
                        ) AS exit_reason
                    FROM trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                      AND coalesce(is_invalid,false)=false
                      AND (
                            payload->>'intent_type' = 'EXIT'
                         OR payload->'features'->>'is_exit' = 'True'
                         OR payload->'features'->>'is_exit' = 'true'
                         OR coalesce(payload->>'reason','') IN ('time_exit','stop_loss_long','stop_loss_short','take_profit_long','take_profit_short')
                         OR coalesce(payload->'features'->>'reason','') IN ('time_exit','stop_loss_long','stop_loss_short','take_profit_long','take_profit_short')
                      )
                ),
                joined AS (
                    SELECT
                        ct.id,
                        coalesce(ct.root_symbol,
                            CASE
                                WHEN left(ct.symbol, 2) = 'BR' THEN 'BR'
                                WHEN left(ct.symbol, 2) = 'NG' THEN 'NG'
                                ELSE 'OTHER'
                            END
                        ) AS root,
                        ct.symbol,
                        ct.net_pnl::numeric AS net_pnl,
                        coalesce(ee.exit_reason, 'NO_MATCH') AS exit_reason,
                        row_number() OVER (
                            PARTITION BY ct.id
                            ORDER BY abs(extract(epoch FROM (
                                coalesce(ct.exit_ts, ct.closed_at, ct.created_at) - ee.exit_event_ts
                            ))) ASC NULLS LAST
                        ) AS rn
                    FROM closed_trades ct
                    LEFT JOIN exit_events ee
                      ON ee.symbol = ct.symbol
                     AND abs(extract(epoch FROM (
                         coalesce(ct.exit_ts, ct.closed_at, ct.created_at) - ee.exit_event_ts
                     ))) <= %s
                    WHERE left(ct.symbol, 2) IN ('BR','NG')
                ),
                best AS (
                    SELECT
                        root,
                        symbol,
                        net_pnl,
                        CASE
                            WHEN exit_reason = 'time_exit' THEN 'TIME_EXIT'
                            WHEN exit_reason = 'NO_MATCH' THEN 'NO_MATCH'
                            ELSE 'OTHER_EXIT'
                        END AS bucket
                    FROM joined
                    WHERE rn = 1
                )
                SELECT
                    root,
                    bucket,
                    count(*) AS trades,
                    count(*) FILTER (WHERE net_pnl > 0) AS wins,
                    count(*) FILTER (WHERE net_pnl < 0) AS losses,
                    round(sum(net_pnl), 6) AS net_pnl,
                    round(avg(net_pnl), 6) AS expectancy,
                    CASE
                        WHEN abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)) > 0
                        THEN round(
                            (sum(net_pnl) FILTER (WHERE net_pnl > 0))
                            / abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)),
                            6
                        )
                        ELSE NULL
                    END AS profit_factor
                FROM best
                GROUP BY 1,2
                ORDER BY root, bucket;
                """,
                (MAX_JOIN_SECONDS,),
            )

            for r in cur.fetchall():
                pf = r["profit_factor"]
                exp = float(r["expectancy"] or 0)
                trades = int(r["trades"] or 0)

                if trades < 20:
                    status = "INSUFFICIENT_DATA"
                elif exp > 0 and (pf is not None and float(pf) >= 1.20):
                    status = "ACTIVE"
                elif exp > 0 and (pf is not None and float(pf) >= 0.90):
                    status = "WATCH"
                else:
                    status = "NOISE"

                print(
                    f"BUCKET_ROW root={r['root']} bucket={r['bucket']} "
                    f"trades={r['trades']} wins={r['wins']} losses={r['losses']} "
                    f"net_pnl={r['net_pnl']} expectancy={r['expectancy']} "
                    f"profit_factor={r['profit_factor']} status={status}"
                )
            print()

            print("MATCH_COVERAGE")
            cur.execute(
                """
                WITH exit_events AS (
                    SELECT symbol, ts AS exit_event_ts
                    FROM trades
                    WHERE left(symbol, 2) IN ('BR','NG')
                      AND coalesce(is_invalid,false)=false
                      AND (
                            payload->>'intent_type' = 'EXIT'
                         OR payload->'features'->>'is_exit' = 'True'
                         OR payload->'features'->>'is_exit' = 'true'
                      )
                ),
                joined AS (
                    SELECT
                        ct.id,
                        CASE
                            WHEN left(ct.symbol, 2) = 'BR' THEN 'BR'
                            WHEN left(ct.symbol, 2) = 'NG' THEN 'NG'
                            ELSE 'OTHER'
                        END AS root,
                        count(ee.exit_event_ts) AS matches
                    FROM closed_trades ct
                    LEFT JOIN exit_events ee
                      ON ee.symbol = ct.symbol
                     AND abs(extract(epoch FROM (
                         coalesce(ct.exit_ts, ct.closed_at, ct.created_at) - ee.exit_event_ts
                     ))) <= %s
                    WHERE left(ct.symbol, 2) IN ('BR','NG')
                    GROUP BY ct.id, root
                )
                SELECT
                    root,
                    count(*) AS closed_trades,
                    count(*) FILTER (WHERE matches > 0) AS matched_trades,
                    count(*) FILTER (WHERE matches = 0) AS unmatched_trades
                FROM joined
                GROUP BY root
                ORDER BY root;
                """,
                (MAX_JOIN_SECONDS,),
            )
            for r in cur.fetchall():
                print(
                    f"COVERAGE_ROW root={r['root']} closed_trades={r['closed_trades']} "
                    f"matched_trades={r['matched_trades']} unmatched_trades={r['unmatched_trades']}"
                )
            print()

    print("VERDICT=TIME_EXIT_QUALITY_JOIN_RECORDED")
    print("TIME_EXIT_QUALITY_JOIN_V1_OK")


if __name__ == "__main__":
    main()
