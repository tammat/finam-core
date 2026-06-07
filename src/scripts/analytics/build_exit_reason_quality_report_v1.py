#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from typing import Iterable

import psycopg2
import psycopg2.extras


ALLOWED_GROUPS = {
    "exit_reason": "exit_reason",
    "symbol": "symbol",
    "side": "side",
    "hour_msk": "hour_msk",
    "hold_bucket": "hold_bucket",
    "strategy": "strategy",
    "timeframe": "timeframe",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default="", help="Root filter: NG, BR, etc.")
    p.add_argument("--symbol", default="", help="Exact symbol filter, e.g. NGN6@RTSX")
    p.add_argument("--source", default="closed_trade_engine_v1_1")
    p.add_argument("--trusted-from", required=True)
    p.add_argument("--exit-reason", default="", help="Optional exact exit_reason filter")
    p.add_argument(
        "--group-by",
        default="exit_reason,hour_msk,hold_bucket,side",
        help="Comma-separated: exit_reason,symbol,side,hour_msk,hold_bucket,strategy,timeframe",
    )
    p.add_argument("--limit", type=int, default=200)
    return p.parse_args()


def pf_sql() -> str:
    return """
        CASE
            WHEN abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)) IS NULL
              OR abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)) = 0
            THEN NULL
            ELSE
                (sum(net_pnl) FILTER (WHERE net_pnl > 0))
                / abs(sum(net_pnl) FILTER (WHERE net_pnl < 0))
        END
    """


def normalize_groups(raw: str) -> list[str]:
    groups = [x.strip() for x in raw.split(",") if x.strip()]
    invalid = [g for g in groups if g not in ALLOWED_GROUPS]
    if invalid:
        raise SystemExit(f"INVALID_GROUP_BY={','.join(invalid)}")
    if not groups:
        raise SystemExit("GROUP_BY_REQUIRED")
    return groups


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
    groups = normalize_groups(args.group_by)
    where, params = build_where(args)

    print("=== EXIT REASON QUALITY REPORT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("report=parametric")
    print(f"root={args.root or 'ANY'}")
    print(f"symbol={args.symbol or 'ANY'}")
    print(f"source={args.source}")
    print(f"trusted_from={args.trusted_from}")
    print(f"exit_reason_filter={args.exit_reason or 'ANY'}")
    print(f"group_by={','.join(groups)}")
    print()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    select_groups = ", ".join(ALLOWED_GROUPS[g] for g in groups)
    order_groups = ", ".join(ALLOWED_GROUPS[g] for g in groups)

    sql = f"""
        WITH base AS (
            SELECT
                id,
                symbol,
                side,
                strategy,
                timeframe,
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
        )
        SELECT
            {select_groups},
            count(*) AS trades,
            count(*) FILTER (WHERE net_pnl > 0) AS wins,
            count(*) FILTER (WHERE net_pnl < 0) AS losses,
            round(
                (count(*) FILTER (WHERE net_pnl > 0)::numeric / nullif(count(*), 0)),
                6
            )::float AS winrate,
            round(coalesce(sum(net_pnl) FILTER (WHERE net_pnl > 0), 0)::numeric, 6)::float AS gross_profit,
            round(coalesce(sum(net_pnl) FILTER (WHERE net_pnl < 0), 0)::numeric, 6)::float AS gross_loss,
            round(sum(net_pnl)::numeric, 6)::float AS net_pnl,
            round(avg(net_pnl)::numeric, 6)::float AS expectancy,
            round(({pf_sql()})::numeric, 6)::float AS profit_factor
        FROM base
        GROUP BY {select_groups}
        ORDER BY trades DESC, {order_groups}
        LIMIT %s
    """
    params.append(args.limit)

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()

    print("QUALITY_ROWS")
    if not rows:
        print("NONE")

    for r in rows:
        group_text = " ".join(f"{g}={r[g]}" for g in groups)
        pf = r["profit_factor"]
        pf_text = "None" if pf is None else f"{float(pf):.6f}"
        print(
            f"QUALITY_ROW {group_text} "
            f"trades={r['trades']} wins={r['wins']} losses={r['losses']} "
            f"winrate={float(r['winrate'] or 0):.6f} "
            f"gross_profit={float(r['gross_profit'] or 0):.6f} "
            f"gross_loss={float(r['gross_loss'] or 0):.6f} "
            f"net_pnl={float(r['net_pnl'] or 0):.6f} "
            f"expectancy={float(r['expectancy'] or 0):.6f} "
            f"profit_factor={pf_text}"
        )

    print()
    print("SUMMARY")
    print(f"ROWS={len(rows)}")
    print("VERDICT=EXIT_REASON_QUALITY_RECORDED")
    print("EXIT_REASON_QUALITY_REPORT_V1_OK")


if __name__ == "__main__":
    main()
