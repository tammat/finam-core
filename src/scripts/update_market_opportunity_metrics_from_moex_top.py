from __future__ import annotations

import os
import subprocess


TOP_N = int(os.getenv("MOEX_TOP_TO_OPPORTUNITY_LIMIT", "30"))


SQL = f"""
insert into market_opportunity_metrics (
    symbol,
    asset_class,
    atr_pct,
    rvol,
    turnover,
    spread_pct,
    regime,
    is_tradeable,
    raw,
    smart_money_score,
    smart_money_label,
    calculated_at
)
with latest as (
    select max(calculated_at) as calculated_at
    from moex_top_universe
),
src as (
    select m.*
    from moex_top_universe m
    join latest l on l.calculated_at = m.calculated_at
    order by m.total_score desc nulls last
    limit {TOP_N}
)
select
    src.symbol,
    src.asset_class,
    coalesce(src.intraday_range_pct, 0) as atr_pct,
    coalesce(src.volume_score, 0) * 5.0 as rvol,
    coalesce(src.value_today, 0) as turnover,
    0.0 as spread_pct,
    case
        when coalesce(src.intraday_range_pct, 0) >= 0.02 then 'trend_up_high_vol'
        when coalesce(src.intraday_range_pct, 0) >= 0.01 then 'trend_up'
        else 'unknown_trend_unknown_vol'
    end as regime,
    true as is_tradeable,
    jsonb_build_object(
        'source', 'moex_top_universe',
        'top_score', src.total_score,
        'reason', src.reason,
        'board', src.board,
        'short_name', src.short_name
    ) as raw,
    0.0 as smart_money_score,
    'NO_SMART_MONEY_DATA' as smart_money_label,
    now() as calculated_at
from src
where src.symbol is not null;
"""


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    result = subprocess.run(
        ["psql", database_url, "-P", "pager=off", "-v", "ON_ERROR_STOP=1", "-c", SQL],
        text=True,
        capture_output=True,
        check=True,
    )

    print(result.stdout)
    print("OK: market opportunity metrics updated from moex_top_universe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
