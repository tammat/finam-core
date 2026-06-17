#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import psycopg2
import psycopg2.extras


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    return proc.stdout or ""


def main() -> int:
    print("=== NGQ6 FORWARD ACCUMULATION VERIFY V3 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    journal = run([
        "journalctl",
        "-u",
        "finam-paper-pipeline.service",
        "--since",
        "30 minutes ago",
        "--no-pager",
    ])

    lines = journal.splitlines()

    cluster_advisory = sum(
        1 for x in lines
        if "PIPE_CLUSTER_BLOCK_ADVISORY_CONTINUE" in x
        and "symbol=NGQ6@RTSX" in x
    )

    trade_exec = sum(
        1 for x in lines
        if "PIPE_TRADE_EXEC symbol=NGQ6@RTSX" in x
    )

    fills = sum(
        1 for x in lines
        if "PIPE_FILLED paper NGQ6@RTSX" in x
    )

    persisted = sum(
        1 for x in lines
        if "PIPE_FILL_PERSISTED" in x
        and "NGQ6@RTSX" in x
    )

    print(f"LOG_NGQ6_CLUSTER_ADVISORY={cluster_advisory}")
    print(f"LOG_NGQ6_TRADE_EXEC={trade_exec}")
    print(f"LOG_NGQ6_FILLS={fills}")
    print(f"LOG_NGQ6_FILL_PERSISTED={persisted}")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                select
                    id,
                    created_at,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    origin,
                    trade_source,
                    qty,
                    price
                from trades
                where symbol='NGQ6@RTSX'
                  and created_at >= now() - interval '60 minutes'
                order by created_at desc
                limit 20;
            """)
            recent_trades = cur.fetchall()

            cur.execute("""
                select
                    coalesce(timeframe,'') as timeframe,
                    coalesce(strategy,'') as strategy,
                    count(*) as rows_count
                from trades
                where symbol='NGQ6@RTSX'
                  and created_at >= now() - interval '60 minutes'
                group by 1,2
                order by rows_count desc;
            """)
            identity_rows = cur.fetchall()

            cur.execute("""
                select
                    symbol,
                    strategy,
                    timeframe,
                    clean_trades,
                    trade_days,
                    v3_full_chains,
                    round(v3_net_pnl,6) as pnl,
                    accumulation_status
                from clean_paper_accumulation_tracker_v1
                where symbol='NGQ6@RTSX'
                order by strategy,timeframe;
            """)
            v3_rows = cur.fetchall()

    print()
    print("RECENT_NGQ6_TRADES")
    for r in recent_trades:
        print(
            "TRADE_ROW "
            f"id={r['id']} "
            f"created_at={r['created_at']} "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"side={r['side']} "
            f"origin={r['origin']} "
            f"trade_source={r['trade_source']} "
            f"qty={r['qty']} "
            f"price={r['price']}"
        )

    print()
    print("RECENT_IDENTITY_SUMMARY")
    for r in identity_rows:
        print(
            "IDENTITY_ROW "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"rows={r['rows_count']}"
        )

    print()
    print("CURRENT_V3_NGQ6")
    for r in v3_rows:
        print(
            "V3_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"clean_trades={r['clean_trades']} "
            f"trade_days={r['trade_days']} "
            f"v3_full_chains={r['v3_full_chains']} "
            f"pnl={r['pnl']} "
            f"status={r['accumulation_status']}"
        )

    has_recent_trade = len(recent_trades) > 0
    has_m1_trade = any(
        r["strategy"] == "NG_CONSERVATIVE_BREAKOUT_M1"
        and r["timeframe"] == "M1"
        for r in recent_trades
    )
    has_live_trade = any(
        r["strategy"] == "NG_CONSERVATIVE_BREAKOUT_M1"
        and r["timeframe"] == "LIVE"
        for r in recent_trades
    )

    if fills == 0:
        verdict = "NO_RECENT_NGQ6_FILL"
    elif not has_recent_trade:
        verdict = "FILL_LOGGED_BUT_NO_DB_TRADE"
    elif has_live_trade and not has_m1_trade:
        verdict = "NGQ6_FILL_OK_TIMEFRAME_LIVE_FIX_REQUIRED"
    elif has_m1_trade:
        verdict = "NGQ6_FORWARD_TRADE_IDENTITY_OK"
    else:
        verdict = "NGQ6_FORWARD_TRADE_UNKNOWN_IDENTITY"

    print()
    print(f"VERDICT={verdict}")
    print("NGQ6_FORWARD_ACCUMULATION_VERIFY_V3_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
