#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os

import psycopg2
import psycopg2.extras


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default="")
    p.add_argument("--symbol", default="")
    p.add_argument("--source", default="closed_trade_engine_v1_1")
    p.add_argument("--trusted-from", required=True)
    p.add_argument("--exit-reason", default="")
    p.add_argument("--min-trades", type=int, default=2)
    p.add_argument("--limit", type=int, default=10)
    return p.parse_args()


def build_where(args: argparse.Namespace) -> tuple[list[str], list[object]]:
    where = [
        "source = %s",
        "COALESCE(exit_ts, closed_at, created_at) >= %s",
    ]
    params: list[object] = [args.source, args.trusted_from]

    if args.root:
        where.append("symbol LIKE %s")
        params.append(f"{args.root}%")

    if args.symbol:
        where.append("symbol = %s")
        params.append(args.symbol)

    if args.exit_reason:
        where.append("COALESCE(NULLIF(payload->>'exit_reason', ''), 'NO_MATCH') = %s")
        params.append(args.exit_reason)

    return where, params


def main() -> None:
    args = parse_args()
    where, params = build_where(args)

    print("=== EXIT REASON TOP CLUSTERS V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("report=parametric_top_bottom_clusters")
    print(f"root={args.root or 'ANY'}")
    print(f"symbol={args.symbol or 'ANY'}")
    print(f"source={args.source}")
    print(f"trusted_from={args.trusted_from}")
    print(f"exit_reason_filter={args.exit_reason or 'ANY'}")
    print(f"min_trades={args.min_trades}")
    print(f"limit={args.limit}")
    print()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    sql = f"""
        WITH base AS (
            SELECT
                symbol,
                side,
                COALESCE(NULLIF(payload->>'exit_reason', ''), 'NO_MATCH') AS exit_reason,
                EXTRACT(
                    HOUR FROM (
                        COALESCE(exit_ts, closed_at, created_at)
                        AT TIME ZONE 'Europe/Moscow'
                    )
                )::int AS hour_msk,
                CASE
                    WHEN COALESCE(hold_seconds, holding_seconds, 0) < 1800 THEN '0-30m'
                    WHEN COALESCE(hold_seconds, holding_seconds, 0) < 3600 THEN '30-60m'
                    WHEN COALESCE(hold_seconds, holding_seconds, 0) < 7200 THEN '1-2h'
                    WHEN COALESCE(hold_seconds, holding_seconds, 0) < 14400 THEN '2-4h'
                    WHEN COALESCE(hold_seconds, holding_seconds, 0) < 28800 THEN '4-8h'
                    ELSE '8h+'
                END AS hold_bucket,
                net_pnl::float AS net_pnl
            FROM closed_trades
            WHERE {" AND ".join(where)}
        ),
        clusters AS (
            SELECT
                exit_reason,
                hour_msk,
                hold_bucket,
                side,
                count(*) AS trades,
                count(*) FILTER (WHERE net_pnl > 0) AS wins,
                count(*) FILTER (WHERE net_pnl < 0) AS losses,
                round(sum(net_pnl)::numeric, 6)::float AS net_pnl,
                round(avg(net_pnl)::numeric, 6)::float AS expectancy,
                round(
                    (count(*) FILTER (WHERE net_pnl > 0)::numeric / nullif(count(*),0)),
                    6
                )::float AS winrate,
                round(coalesce(sum(net_pnl) FILTER (WHERE net_pnl > 0),0)::numeric, 6)::float AS gross_profit,
                round(coalesce(sum(net_pnl) FILTER (WHERE net_pnl < 0),0)::numeric, 6)::float AS gross_loss,
                CASE
                    WHEN abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)) IS NULL
                      OR abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)) = 0
                    THEN NULL
                    ELSE round(
                        (
                            (sum(net_pnl) FILTER (WHERE net_pnl > 0))
                            / abs(sum(net_pnl) FILTER (WHERE net_pnl < 0))
                        )::numeric,
                        6
                    )::float
                END AS profit_factor
            FROM base
            GROUP BY exit_reason, hour_msk, hold_bucket, side
            HAVING count(*) >= %s
        )
        SELECT *, 'TOP' AS bucket
        FROM clusters
        ORDER BY expectancy DESC, net_pnl DESC
        LIMIT %s
    """

    bottom_sql = sql.replace(
        "SELECT *, 'TOP' AS bucket\n        FROM clusters\n        ORDER BY expectancy DESC, net_pnl DESC\n        LIMIT %s",
        "SELECT *, 'BOTTOM' AS bucket\n        FROM clusters\n        ORDER BY expectancy ASC, net_pnl ASC\n        LIMIT %s",
    )

    qparams = tuple(params + [args.min_trades, args.limit])

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, qparams)
            top_rows = cur.fetchall()
            cur.execute(bottom_sql, qparams)
            bottom_rows = cur.fetchall()

    def print_block(title: str, rows) -> None:
        print(title)
        if not rows:
            print("NONE")
        for r in rows:
            pf = r["profit_factor"]
            pf_text = "None" if pf is None else f"{float(pf):.6f}"
            print(
                f"CLUSTER_ROW bucket={r['bucket']} "
                f"exit_reason={r['exit_reason']} hour_msk={r['hour_msk']} "
                f"hold_bucket={r['hold_bucket']} side={r['side']} "
                f"trades={r['trades']} wins={r['wins']} losses={r['losses']} "
                f"winrate={float(r['winrate'] or 0):.6f} "
                f"net_pnl={float(r['net_pnl'] or 0):.6f} "
                f"expectancy={float(r['expectancy'] or 0):.6f} "
                f"profit_factor={pf_text}"
            )
        print()

    print_block("TOP_CLUSTERS", top_rows)
    print_block("BOTTOM_CLUSTERS", bottom_rows)

    print("SUMMARY")
    print(f"TOP_ROWS={len(top_rows)}")
    print(f"BOTTOM_ROWS={len(bottom_rows)}")
    print("VERDICT=EXIT_REASON_TOP_CLUSTERS_RECORDED")
    print("EXIT_REASON_TOP_CLUSTERS_V1_OK")


if __name__ == "__main__":
    main()
