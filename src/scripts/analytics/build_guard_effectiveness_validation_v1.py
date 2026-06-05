#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def metrics(rows):
    trades = len(rows)
    pnl = sum(float(r[0] or 0) for r in rows)
    wins = sum(1 for r in rows if float(r[0] or 0) > 0)
    losses = sum(1 for r in rows if float(r[0] or 0) < 0)
    gross_profit = sum(float(r[0] or 0) for r in rows if float(r[0] or 0) > 0)
    gross_loss = abs(sum(float(r[0] or 0) for r in rows if float(r[0] or 0) < 0))
    pf = None if gross_loss == 0 else gross_profit / gross_loss
    expectancy = 0 if trades == 0 else pnl / trades
    winrate = 0 if trades == 0 else wins / trades
    return trades, pnl, wins, losses, winrate, expectancy, pf


def print_row(label, rows):
    trades, pnl, wins, losses, winrate, expectancy, pf = metrics(rows)
    print(
        f"{label} trades={trades} wins={wins} losses={losses} "
        f"winrate={winrate:.4f} net_pnl={pnl:.8f} "
        f"expectancy={expectancy:.8f} "
        f"profit_factor={'None' if pf is None else f'{pf:.8f}'}"
    )
    return trades, pnl, pf


def main():
    sql = """
        select
            ct.net_pnl,
            ct.symbol,
            ct.strategy,
            ct.timeframe,
            ct.side,
            coalesce(ct.payload->'entry_payload'->>'session_bucket', 'UNKNOWN') as session_bucket,
            coalesce(g.classification, 'NO_CLASSIFICATION') as classification
        from closed_trades ct
        left join guard_candidate_classification_state g
          on g.symbol = ct.symbol
         and g.strategy = ct.strategy
         and g.timeframe = ct.timeframe
         and g.side = ct.side
         and g.session_bucket = coalesce(ct.payload->'entry_payload'->>'session_bucket', 'UNKNOWN')
         and g.source = 'guard_candidate_classification_v1'
        where ct.source = 'closed_trade_engine_v1_1'
          and ct.trade_source = 'paper'
        order by ct.symbol, ct.strategy, ct.timeframe, ct.side;
    """

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    all_rows = rows
    block_rows = [r for r in rows if r[6] == "BLOCK_READY"]
    research_rows = [r for r in rows if r[6] == "RESEARCH_ONLY"]
    keep_rows = [r for r in rows if r[6] == "KEEP_WATCH"]
    no_class_rows = [r for r in rows if r[6] == "NO_CLASSIFICATION"]
    without_block_rows = [r for r in rows if r[6] != "BLOCK_READY"]

    print("=== GUARD EFFECTIVENESS VALIDATION V1 ===")
    print()

    all_trades, all_pnl, all_pf = print_row("ALL_TRADES", all_rows)
    block_trades, block_pnl, block_pf = print_row("BLOCK_READY_REMOVED_SET", block_rows)
    research_trades, research_pnl, research_pf = print_row("RESEARCH_ONLY_SET", research_rows)
    keep_trades, keep_pnl, keep_pf = print_row("KEEP_WATCH_SET", keep_rows)
    no_class_trades, no_class_pnl, no_class_pf = print_row("NO_CLASSIFICATION_SET", no_class_rows)
    filtered_trades, filtered_pnl, filtered_pf = print_row("WITHOUT_BLOCK_READY", without_block_rows)

    print()
    print(
        f"DELTA trades_removed={block_trades} "
        f"net_pnl_removed={block_pnl:.8f} "
        f"net_pnl_after_filter={filtered_pnl:.8f} "
        f"net_pnl_improvement={(filtered_pnl - all_pnl):.8f}"
    )

    if all_pf is not None and filtered_pf is not None:
        print(f"DELTA_PF profit_factor_before={all_pf:.8f} profit_factor_after={filtered_pf:.8f} improvement={(filtered_pf - all_pf):.8f}")
    else:
        print("DELTA_PF profit_factor_before_or_after=None")

    verdict = "GUARD_EFFECTIVE" if filtered_pnl > all_pnl else "GUARD_NOT_EFFECTIVE"
    print(f"VERDICT={verdict}")


if __name__ == "__main__":
    main()
