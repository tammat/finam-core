from __future__ import annotations

import os
import subprocess


MIN_FILLS = int(os.getenv("REGIME_CONTROL_MIN_FILLS", "3"))
MIN_AVG_CASHFLOW_HEALTHY = float(os.getenv("REGIME_CONTROL_MIN_AVG_CASHFLOW_HEALTHY", "0.0"))
MIN_AVG_CASHFLOW_DEGRADED = float(os.getenv("REGIME_CONTROL_MIN_AVG_CASHFLOW_DEGRADED", "-0.05"))


def run_psql(sql: str) -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    result = subprocess.run(
        ["psql", database_url, "-P", "pager=off", "-v", "ON_ERROR_STOP=1", "-c", sql],
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


def main() -> int:
    sql = f"""
with regime_stats as (
    select
        analytics_symbol,
        strategy,
        regime,
        sum(fills) as fills,
        sum(signed_cashflow) as signed_cashflow,
        round((sum(signed_cashflow) / nullif(sum(fills), 0))::numeric, 6) as avg_signed_cashflow,
        round(avg(avg_confidence)::numeric, 4) as avg_confidence
    from analytics_strategy_regime_attribution_v2
    where strategy is not null
      and strategy <> ''
      and regime is not null
      and regime <> ''
    group by analytics_symbol, strategy, regime
)
insert into strategy_runtime_regime_control (
    symbol, strategy, regime, status, allow_trade, watch_only,
    risk_multiplier, reason, updated_at
)
select
    analytics_symbol as symbol,
    strategy,
    regime,
    case
        when fills < {MIN_FILLS} then 'NO_DATA'
        when avg_signed_cashflow >= {MIN_AVG_CASHFLOW_HEALTHY} then 'HEALTHY'
        when avg_signed_cashflow >= {MIN_AVG_CASHFLOW_DEGRADED} then 'DEGRADED'
        else 'BLOCKED'
    end as status,
    case
        when fills < {MIN_FILLS} then false
        when avg_signed_cashflow >= {MIN_AVG_CASHFLOW_DEGRADED} then true
        else false
    end as allow_trade,
    case
        when fills < {MIN_FILLS} then true
        when avg_signed_cashflow >= {MIN_AVG_CASHFLOW_DEGRADED} then false
        else true
    end as watch_only,
    case
        when fills < {MIN_FILLS} then 0.0
        when avg_signed_cashflow >= {MIN_AVG_CASHFLOW_HEALTHY} then 1.0
        when avg_signed_cashflow >= {MIN_AVG_CASHFLOW_DEGRADED} then 0.5
        else 0.0
    end as risk_multiplier,
    concat(
        'regime_applier_v1:',
        'fills=', fills,
        ';signed_cashflow=', signed_cashflow,
        ';avg_signed_cashflow=', avg_signed_cashflow,
        ';confidence=', coalesce(avg_confidence::text, 'null')
    ) as reason,
    now() as updated_at
from regime_stats
on conflict (symbol, strategy, regime) do update set
    status = excluded.status,
    allow_trade = excluded.allow_trade,
    watch_only = excluded.watch_only,
    risk_multiplier = excluded.risk_multiplier,
    reason = excluded.reason,
    updated_at = now();"""
    print(run_psql(sql))
    print("OK: applied regime-aware runtime control v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
