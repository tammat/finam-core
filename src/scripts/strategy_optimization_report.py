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
            "-v",
            "ON_ERROR_STOP=1",
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
    parser.add_argument("--min-trades", type=int, default=3)
    parser.add_argument("--out", default="reports/strategy_optimization_report.tsv")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    since_expr = f"now() - interval '{int(args.days)} days'"
    min_trades = int(args.min_trades)

    clean_filter = f"""
where coalesce(exit_ts, created_at) >= {since_expr}
  and payload ? 'entry_payload'
  and coalesce(payload->'entry_payload'->>'origin', '') <> 'backfill_from_fills'
  and coalesce(strategy, payload->'entry_payload'->>'strategy', '') not in ('', 'UNKNOWN')
  and coalesce(signal_id, payload->'entry_payload'->>'signal_id', '') <> ''
"""

    sections = {
        "ЛУЧШИЕ_СВЯЗКИ": f"""
select
  symbol,
  strategy,
  coalesce(regime, 'UNKNOWN') as regime,
  coalesce(horizon, 'UNKNOWN') as horizon,
  count(*) as trades,
  round(sum(net_pnl)::numeric, 4) as net_pnl,
  round(avg(net_pnl)::numeric, 4) as expectancy,
  round((sum(case when net_pnl > 0 then 1 else 0 end)::numeric / nullif(count(*), 0) * 100), 2) as winrate_pct,
  round(
    (sum(case when net_pnl > 0 then net_pnl else 0 end)::numeric /
     nullif(abs(sum(case when net_pnl < 0 then net_pnl else 0 end))::numeric, 0)),
    4
  ) as profit_factor
from closed_trades
{clean_filter}
group by 1,2,3,4
having count(*) >= {min_trades}
order by net_pnl desc, profit_factor desc
limit 30;
""",
        "ХУДШИЕ_СВЯЗКИ": f"""
select
  symbol,
  strategy,
  coalesce(regime, 'UNKNOWN') as regime,
  coalesce(horizon, 'UNKNOWN') as horizon,
  count(*) as trades,
  round(sum(net_pnl)::numeric, 4) as net_pnl,
  round(avg(net_pnl)::numeric, 4) as expectancy,
  round((sum(case when net_pnl > 0 then 1 else 0 end)::numeric / nullif(count(*), 0) * 100), 2) as winrate_pct
from closed_trades
{clean_filter}
group by 1,2,3,4
having count(*) >= {min_trades}
order by net_pnl asc, expectancy asc
limit 30;
""",
        "PNL_ПО_ЧАСАМ": f"""
select
  symbol,
  strategy,
  extract(hour from coalesce(exit_ts, created_at))::int as exit_hour_utc,
  count(*) as trades,
  round(sum(net_pnl)::numeric, 4) as net_pnl,
  round(avg(net_pnl)::numeric, 4) as expectancy,
  round((sum(case when net_pnl > 0 then 1 else 0 end)::numeric / nullif(count(*), 0) * 100), 2) as winrate_pct
from closed_trades
{clean_filter}
group by 1,2,3
having count(*) >= {min_trades}
order by symbol, strategy, exit_hour_utc;
""",
        "PNL_ПО_РЕЖИМАМ": f"""
select
  symbol,
  strategy,
  coalesce(regime, 'UNKNOWN') as regime,
  count(*) as trades,
  round(sum(net_pnl)::numeric, 4) as net_pnl,
  round(avg(net_pnl)::numeric, 4) as expectancy,
  round((sum(case when net_pnl > 0 then 1 else 0 end)::numeric / nullif(count(*), 0) * 100), 2) as winrate_pct
from closed_trades
{clean_filter}
group by 1,2,3
having count(*) >= {min_trades}
order by net_pnl desc;
""",
        "КАНДИДАТЫ_НА_ОТКЛЮЧЕНИЕ": f"""
select
  symbol,
  strategy,
  count(*) as trades,
  round(sum(net_pnl)::numeric, 4) as net_pnl,
  round(avg(net_pnl)::numeric, 4) as expectancy,
  round((sum(case when net_pnl > 0 then 1 else 0 end)::numeric / nullif(count(*), 0) * 100), 2) as winrate_pct
from closed_trades
{clean_filter}
group by 1,2
having count(*) >= {min_trades}
   and sum(net_pnl) < 0
order by net_pnl asc;
""",
        "КАНДИДАТЫ_НА_УСИЛЕНИЕ": f"""
select
  symbol,
  strategy,
  count(*) as trades,
  round(sum(net_pnl)::numeric, 4) as net_pnl,
  round(avg(net_pnl)::numeric, 4) as expectancy,
  round((sum(case when net_pnl > 0 then 1 else 0 end)::numeric / nullif(count(*), 0) * 100), 2) as winrate_pct
from closed_trades
{clean_filter}
group by 1,2
having count(*) >= {min_trades}
   and sum(net_pnl) > 0
order by net_pnl desc;
""",
        "ДОЛГ_ПО_ДАННЫМ_UNKNOWN": f"""
select
  symbol,
  coalesce(trade_source, 'unknown') as trade_source,
  count(*) as closed_trades,
  round(sum(net_pnl)::numeric, 4) as net_pnl,
  count(*) filter (where coalesce(strategy, '') in ('', 'UNKNOWN')) as missing_strategy,
  count(*) filter (where coalesce(signal_id, '') = '') as missing_signal_id
from closed_trades
where coalesce(exit_ts, created_at) >= {since_expr}
  and (
    coalesce(strategy, '') in ('', 'UNKNOWN')
    or coalesce(signal_id, '') = ''
  )
group by 1,2
order by closed_trades desc;
""",
    }

    if args.dry_run:
        for title, sql in sections.items():
            print(f"\n## {title}\n{sql.strip()}")
        return 0

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as out:
        out.write("ОТЧЁТ ПО ОПТИМИЗАЦИИ СТРАТЕГИЙ V1\n")
        out.write(f"period_days\t{args.days}\n")
        out.write(f"min_trades\t{args.min_trades}\n")
        for title, sql in sections.items():
            write_section(out, title, sql)

    print(f"OK: отчёт записан в {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
