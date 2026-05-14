from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def run_psql(sql: str) -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    result = subprocess.run(
        [
            "psql",
            database_url,
            "-P",
            "pager=off",
            "-F",
            "\t",
            "-A",
            "-c",
            sql,
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def write_section(out, title: str, sql: str) -> None:
    out.write(f"\n## {title}\n")
    out.write(run_psql(sql))
    out.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--out", default="reports/strategy_performance_report.tsv")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    since_expr = f"now() - interval '{int(args.days)} days'"

    sections = {
        "SIGNALS_BY_STRATEGY": f"""
select
  coalesce(symbol, 'UNKNOWN') as symbol,
  coalesce(strategy, 'UNKNOWN') as strategy,
  coalesce(timeframe, 'UNKNOWN') as timeframe,
  coalesce(status, 'UNKNOWN') as status,
  count(*) as signals,
  round(avg(coalesce(confidence, 0))::numeric, 4) as avg_confidence,
  round(avg(coalesce(rr, 0))::numeric, 4) as avg_rr
from signals
where ts >= {since_expr}
group by 1,2,3,4
order by signals desc;
""",
        "RISK_DECISIONS": f"""
select
  coalesce(symbol, 'UNKNOWN') as symbol,
  coalesce(event, 'UNKNOWN') as event,
  coalesce(decision, 'UNKNOWN') as decision,
  count(*) as events
from risk_events
where ts >= {since_expr}
group by 1,2,3
order by events desc;
""",
        "TRADES_BY_SYMBOL_SOURCE": f"""
select
  symbol,
  coalesce(trade_source, 'unknown') as trade_source,
  coalesce(origin, 'unknown') as origin,
  side,
  count(*) as trades,
  round(sum(qty)::numeric, 4) as total_qty,
  round(sum(qty * price)::numeric, 4) as turnover,
  round(sum(coalesce(commission, 0))::numeric, 4) as commission
from trades
where ts >= {since_expr}
group by 1,2,3,4
order by trades desc;
""",
        "REJECTION_REASONS": f"""
select
  coalesce(symbol, 'UNKNOWN') as symbol,
  coalesce(strategy, 'UNKNOWN') as strategy,
  coalesce(rejection_reason, 'NO_REASON') as rejection_reason,
  count(*) as rejected
from signals
where ts >= {since_expr}
  and lower(status) like '%reject%'
group by 1,2,3
order by rejected desc;
""",
        "CLEAN_CLOSED_TRADES_PERFORMANCE": f"""
select
  coalesce(payload->'entry_payload'->>'origin',
           payload->'entry_payload'->>'trade_source',
           payload->'entry_payload'->>'execution_type',
           trade_source,
           'unknown') as source,
  coalesce(symbol, 'UNKNOWN') as symbol,
  coalesce(strategy, 'UNKNOWN') as strategy,
  coalesce(horizon, 'UNKNOWN') as horizon,
  coalesce(regime, 'UNKNOWN') as regime,
  count(*) as closed_trades,
  round(sum(net_pnl)::numeric, 4) as net_pnl,
  round(avg(net_pnl)::numeric, 4) as avg_net_pnl,
  round((sum(case when net_pnl > 0 then 1 else 0 end)::numeric / nullif(count(*), 0) * 100), 2) as winrate_pct,
  round(
    (sum(case when net_pnl > 0 then net_pnl else 0 end)::numeric /
     nullif(abs(sum(case when net_pnl < 0 then net_pnl else 0 end))::numeric, 0)),
    4
  ) as profit_factor
from closed_trades
where coalesce(exit_ts, created_at) >= {since_expr}
  and payload ? 'entry_payload'
  and coalesce(payload->'entry_payload'->>'origin', '') <> 'backfill_from_fills'
group by 1,2,3,4,5
order by net_pnl desc;
""",
        "PNL_BY_SOURCE_SYMBOL": f"""
select
  coalesce(payload->'entry_payload'->>'origin',
           payload->'entry_payload'->>'trade_source',
           payload->'entry_payload'->>'execution_type',
           trade_source,
           'unknown') as source,
  coalesce(symbol, 'UNKNOWN') as symbol,
  coalesce(strategy, 'UNKNOWN') as strategy,
  count(*) as closed_trades,
  round(sum(net_pnl)::numeric, 4) as net_pnl,
  round(avg(net_pnl)::numeric, 4) as avg_net_pnl,
  round((sum(case when net_pnl > 0 then 1 else 0 end)::numeric / nullif(count(*), 0) * 100), 2) as winrate_pct,
  round(
    (sum(case when net_pnl > 0 then net_pnl else 0 end)::numeric /
     nullif(abs(sum(case when net_pnl < 0 then net_pnl else 0 end))::numeric, 0)),
    4
  ) as profit_factor
from closed_trades
where coalesce(exit_ts, created_at) >= {since_expr}
  and coalesce(payload->'entry_payload'->>'origin', '') <> 'backfill_from_fills'
group by 1,2,3
order by net_pnl desc;
""",
        "CLOSED_TRADES_PERFORMANCE": f"""
select
  coalesce(symbol, 'UNKNOWN') as symbol,
  coalesce(strategy, 'UNKNOWN') as strategy,
  coalesce(horizon, 'UNKNOWN') as horizon,
  coalesce(regime, 'UNKNOWN') as regime,
  coalesce(trade_source, 'unknown') as trade_source,
  count(*) as closed_trades,
  round(sum(net_pnl)::numeric, 4) as net_pnl,
  round(sum(gross_pnl)::numeric, 4) as gross_pnl,
  round(sum(commission)::numeric, 4) as commission,
  round(avg(net_pnl)::numeric, 4) as avg_net_pnl,
  round((sum(case when net_pnl > 0 then 1 else 0 end)::numeric / nullif(count(*), 0) * 100), 2) as winrate_pct,
  round(
    (sum(case when net_pnl > 0 then net_pnl else 0 end)::numeric /
     nullif(abs(sum(case when net_pnl < 0 then net_pnl else 0 end))::numeric, 0)),
    4
  ) as profit_factor,
  round(avg(hold_seconds)::numeric, 2) as avg_hold_seconds
from closed_trades
where coalesce(exit_ts, created_at) >= {since_expr}
group by 1,2,3,4,5
order by net_pnl desc;
""",
        "RECENT_TRADES": f"""
select
  ts,
  symbol,
  side,
  qty,
  price,
  commission,
  coalesce(trade_source, 'unknown') as trade_source,
  coalesce(origin, 'unknown') as origin
from trades
order by ts desc
limit 50;
""",
    }

    if args.dry_run:
        for title, sql in sections.items():
            print(f"\n## {title}\n{sql.strip()}")
        return 0

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as out:
        out.write("STRATEGY PERFORMANCE REPORT V1\n")
        out.write(f"period_days\t{args.days}\n")
        for title, sql in sections.items():
            write_section(out, title, sql)

    print(f"OK: report written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
