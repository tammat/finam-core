#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import psycopg2
import psycopg2.extras

SQL = """
select
    a.symbol,
    a.strategy,
    a.timeframe,
    a.trade_source,
    count(*) as trades,
    count(distinct c.entry_ts::date) as entry_days,
    count(distinct c.exit_ts::date) as exit_days,
    count(distinct c.entry_ts) as distinct_entry_ts,
    count(distinct c.exit_ts) as distinct_exit_ts,
    min(c.entry_ts) as first_entry,
    max(c.entry_ts) as last_entry,
    min(c.exit_ts) as first_exit,
    max(c.exit_ts) as last_exit,
    sum(a.pnl) as pnl,
    avg(a.pnl) as expectancy,
    count(*) filter (where a.attribution_quality='FULL') as full_ctx,
    count(*) filter (where a.attribution_quality='PARTIAL') as partial_ctx,
    count(*) filter (where a.attribution_quality='RISK_CONTEXT_WEAK') as weak_ctx
from trade_attribution_v2 a
join closed_trade_chains_v2 c
  on c.id = a.closed_trade_id
where a.symbol=%s
  and a.strategy=%s
  and a.timeframe=%s
  and a.trade_source=%s
group by a.symbol, a.strategy, a.timeframe, a.trade_source;
"""

def make_verdict(row: dict) -> tuple[str, str]:
    trades = int(row["trades"] or 0)
    entry_days = int(row["entry_days"] or 0)
    exit_days = int(row["exit_days"] or 0)

    if trades == 0:
        return "NO_DATA", "нет_сделок_для_проверки"

    if trades >= 100 and (entry_days < 10 or exit_days < 10):
        return "TIMEFRAME_IDENTITY_SUSPECT", "много_сделок_при_низкой_временной_диверсификации"

    if exit_days == 1 and trades >= 30:
        return "TIMEFRAME_IDENTITY_SUSPECT", "много_сделок_закрыто_в_один_день"

    if entry_days >= 20 and exit_days >= 20:
        return "TIMEFRAME_IDENTITY_OK", "временная_диверсификация_достаточная"

    return "RESEARCH_ONLY", "недостаточно_времени_для_подтверждения_identity"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--trade-source", default="paper")
    args = parser.parse_args()

    print("=== STRATEGY IDENTITY AUDIT V1 ===")
    print("mode=research_only")
    print(f"symbol={args.symbol}")
    print(f"strategy={args.strategy}")
    print(f"timeframe={args.timeframe}")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                SQL,
                (args.symbol, args.strategy, args.timeframe, args.trade_source),
            )
            row = cur.fetchone()

    if not row:
        print(
            "STRATEGY_IDENTITY_ROW "
            f"symbol={args.symbol} strategy={args.strategy} timeframe={args.timeframe} "
            "trades=0 verdict=NO_DATA reason=нет_данных "
            "runtime_allow=0 execution_enabled=0"
        )
        print("STRATEGY_IDENTITY_AUDIT_V1_OK")
        return 0

    verdict, reason = make_verdict(row)

    print(
        "STRATEGY_IDENTITY_ROW "
        f"symbol={row['symbol']} "
        f"strategy={row['strategy']} "
        f"timeframe={row['timeframe']} "
        f"trades={int(row['trades'] or 0)} "
        f"entry_days={int(row['entry_days'] or 0)} "
        f"exit_days={int(row['exit_days'] or 0)} "
        f"distinct_entry_ts={int(row['distinct_entry_ts'] or 0)} "
        f"distinct_exit_ts={int(row['distinct_exit_ts'] or 0)} "
        f"pnl={float(row['pnl'] or 0):.4f} "
        f"expectancy={float(row['expectancy'] or 0):.6f} "
        f"full_ctx={int(row['full_ctx'] or 0)} "
        f"partial_ctx={int(row['partial_ctx'] or 0)} "
        f"weak_ctx={int(row['weak_ctx'] or 0)} "
        f"first_entry={row['first_entry']} "
        f"last_entry={row['last_entry']} "
        f"first_exit={row['first_exit']} "
        f"last_exit={row['last_exit']} "
        f"verdict={verdict} "
        f"reason={reason} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("STRATEGY_IDENTITY_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
