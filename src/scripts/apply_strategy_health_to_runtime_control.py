from __future__ import annotations

import argparse
import os
import subprocess


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
            "-A",
            "-F",
            "\t",
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--min-trades", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    since_expr = f"now() - interval '{int(args.days)} days'"
    min_trades = int(args.min_trades)

    decisions_sql = f"""
with perf as (
    select
      symbol,
      strategy,
      coalesce(regime, 'UNKNOWN') as regime,
      count(*) as trades,
      sum(net_pnl) as net_pnl,
      avg(net_pnl) as expectancy,
      (sum(case when net_pnl > 0 then 1 else 0 end)::numeric / nullif(count(*), 0) * 100) as winrate_pct,
      (
        sum(case when net_pnl > 0 then net_pnl else 0 end)::numeric /
        nullif(abs(sum(case when net_pnl < 0 then net_pnl else 0 end))::numeric, 0)
      ) as profit_factor
    from closed_trades
    where coalesce(exit_ts, created_at) >= {since_expr}
      and payload ? 'entry_payload'
      and coalesce(payload->'entry_payload'->>'origin', '') <> 'backfill_from_fills'
      and coalesce(strategy, payload->'entry_payload'->>'strategy', '') not in ('', 'UNKNOWN')
      and coalesce(signal_id, payload->'entry_payload'->>'signal_id', '') <> ''
    group by 1,2,3
    having count(*) >= {min_trades}
),
decisions as (
    select
      symbol,
      strategy,
      regime,
      trades,
      net_pnl,
      expectancy,
      winrate_pct,
      coalesce(profit_factor, 999) as profit_factor,
      case
        when net_pnl > 0 and expectancy > 0 and winrate_pct >= 55 then 'HEALTHY'
        when net_pnl < 0 and expectancy < 0 then 'BLOCKED'
        else 'WATCH'
      end as status,
      case
        when net_pnl > 0 and expectancy > 0 and winrate_pct >= 55 then true
        else false
      end as allow_trade,
      case
        when net_pnl > 0 and expectancy > 0 and winrate_pct >= 55 then false
        else true
      end as watch_only,
      case
        when net_pnl > 0 and expectancy > 0 and winrate_pct >= 55 then 1.2
        when net_pnl < 0 and expectancy < 0 then 0.0
        else 0.0
      end as risk_multiplier,
      case
        when net_pnl > 0 and expectancy > 0 and winrate_pct >= 55
          then 'Положительное матожидание: стратегия разрешена и усилена'
        when net_pnl < 0 and expectancy < 0
          then 'Отрицательное матожидание: стратегия отключена'
        else 'Преимущество не подтверждено: режим наблюдения'
      end as reason
    from perf
)
select
  symbol,
  strategy,
  regime,
  trades,
  round(net_pnl::numeric, 4) as net_pnl,
  round(expectancy::numeric, 4) as expectancy,
  round(winrate_pct::numeric, 2) as winrate_pct,
  round(profit_factor::numeric, 4) as profit_factor,
  status,
  allow_trade,
  watch_only,
  risk_multiplier,
  reason
from decisions
order by net_pnl desc;
"""

    if args.dry_run:
        print(run_psql(decisions_sql))
        return 0

    apply_sql = f"""
with perf as (
    select
      symbol,
      strategy,
      coalesce(regime, 'UNKNOWN') as regime,
      count(*) as trades,
      sum(net_pnl) as net_pnl,
      avg(net_pnl) as expectancy,
      (sum(case when net_pnl > 0 then 1 else 0 end)::numeric / nullif(count(*), 0) * 100) as winrate_pct,
      (
        sum(case when net_pnl > 0 then net_pnl else 0 end)::numeric /
        nullif(abs(sum(case when net_pnl < 0 then net_pnl else 0 end))::numeric, 0)
      ) as profit_factor
    from closed_trades
    where coalesce(exit_ts, created_at) >= {since_expr}
      and payload ? 'entry_payload'
      and coalesce(payload->'entry_payload'->>'origin', '') <> 'backfill_from_fills'
      and coalesce(strategy, payload->'entry_payload'->>'strategy', '') not in ('', 'UNKNOWN')
      and coalesce(signal_id, payload->'entry_payload'->>'signal_id', '') <> ''
    group by 1,2,3
    having count(*) >= {min_trades}
),
decisions as (
    select
      symbol,
      strategy,
      case
        when net_pnl > 0 and expectancy > 0 and winrate_pct >= 55 then 'HEALTHY'
        when net_pnl < 0 and expectancy < 0 then 'BLOCKED'
        else 'WATCH'
      end as status,
      case
        when net_pnl > 0 and expectancy > 0 and winrate_pct >= 55 then true
        else false
      end as allow_trade,
      case
        when net_pnl > 0 and expectancy > 0 and winrate_pct >= 55 then false
        else true
      end as watch_only,
      case
        when net_pnl > 0 and expectancy > 0 and winrate_pct >= 55 then 1.2
        when net_pnl < 0 and expectancy < 0 then 0.0
        else 0.0
      end as risk_multiplier,
      case
        when net_pnl > 0 and expectancy > 0 and winrate_pct >= 55
          then 'Положительное матожидание: стратегия разрешена и усилена'
        when net_pnl < 0 and expectancy < 0
          then 'Отрицательное матожидание: стратегия отключена'
        else 'Преимущество не подтверждено: режим наблюдения'
      end as reason
    from perf
)
insert into strategy_runtime_control (
    symbol,
    strategy,
    status,
    allow_trade,
    watch_only,
    risk_multiplier,
    reason,
    updated_at
)
select
    symbol,
    strategy,
    status,
    allow_trade,
    watch_only,
    risk_multiplier,
    reason,
    now()
from decisions
on conflict (symbol, strategy) do update set
    status = excluded.status,
    allow_trade = excluded.allow_trade,
    watch_only = excluded.watch_only,
    risk_multiplier = excluded.risk_multiplier,
    reason = excluded.reason,
    updated_at = now()
returning symbol, strategy, status, allow_trade, watch_only, risk_multiplier, reason;
"""

    print(run_psql(apply_sql))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
