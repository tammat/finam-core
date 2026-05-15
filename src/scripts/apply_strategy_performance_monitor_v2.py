from __future__ import annotations

import os
import subprocess


MIN_CLOSED_TRADES = int(os.getenv("SPM_V2_MIN_CLOSED_TRADES", "5"))
MIN_PROFIT_FACTOR_HEALTHY = float(os.getenv("SPM_V2_MIN_PF_HEALTHY", "1.15"))
MIN_EXPECTANCY_HEALTHY = float(os.getenv("SPM_V2_MIN_EXPECTANCY_HEALTHY", "0.0"))

MIN_PROFIT_FACTOR_DEGRADED = float(os.getenv("SPM_V2_MIN_PF_DEGRADED", "0.75"))
MIN_EXPECTANCY_DEGRADED = float(os.getenv("SPM_V2_MIN_EXPECTANCY_DEGRADED", "-0.05"))


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
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            sql,
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


def main() -> int:
    sql = f"""
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
    analytics_symbol as symbol,
    strategy,

    case
        when closed_trades < {MIN_CLOSED_TRADES}
            then 'NO_DATA'
        when coalesce(profit_factor, 0) >= {MIN_PROFIT_FACTOR_HEALTHY}
             and expectancy > {MIN_EXPECTANCY_HEALTHY}
            then 'HEALTHY'
        when coalesce(profit_factor, 0) >= {MIN_PROFIT_FACTOR_DEGRADED}
             and expectancy >= {MIN_EXPECTANCY_DEGRADED}
            then 'DEGRADED'
        else 'BLOCKED'
    end as status,

    case
        when closed_trades < {MIN_CLOSED_TRADES}
            then false
        when coalesce(profit_factor, 0) >= {MIN_PROFIT_FACTOR_HEALTHY}
             and expectancy > {MIN_EXPECTANCY_HEALTHY}
            then true
        when coalesce(profit_factor, 0) >= {MIN_PROFIT_FACTOR_DEGRADED}
             and expectancy >= {MIN_EXPECTANCY_DEGRADED}
            then true
        else false
    end as allow_trade,

    case
        when closed_trades < {MIN_CLOSED_TRADES}
            then true
        when coalesce(profit_factor, 0) >= {MIN_PROFIT_FACTOR_HEALTHY}
             and expectancy > {MIN_EXPECTANCY_HEALTHY}
            then false
        when coalesce(profit_factor, 0) >= {MIN_PROFIT_FACTOR_DEGRADED}
             and expectancy >= {MIN_EXPECTANCY_DEGRADED}
            then false
        else true
    end as watch_only,

    case
        when closed_trades < {MIN_CLOSED_TRADES}
            then 0.0
        when coalesce(profit_factor, 0) >= {MIN_PROFIT_FACTOR_HEALTHY}
             and expectancy > {MIN_EXPECTANCY_HEALTHY}
            then 1.0
        when coalesce(profit_factor, 0) >= {MIN_PROFIT_FACTOR_DEGRADED}
             and expectancy >= {MIN_EXPECTANCY_DEGRADED}
            then 0.5
        else 0.0
    end as risk_multiplier,

    concat(
        'spm_v2:',
        'closed_trades=', closed_trades,
        ';expectancy=', expectancy,
        ';pf=', coalesce(profit_factor::text, 'null'),
        ';winrate=', winrate
    ) as reason,

    now() as updated_at
from analytics_strategy_performance_monitor_v2
where strategy is not null
  and strategy <> ''
on conflict (symbol, strategy) do update set
    status = excluded.status,
    allow_trade = excluded.allow_trade,
    watch_only = excluded.watch_only,
    risk_multiplier = excluded.risk_multiplier,
    reason = excluded.reason,
    updated_at = now();
"""
    print(run_psql(sql))
    print("OK: applied StrategyPerformanceMonitor v2 to strategy_runtime_control")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
