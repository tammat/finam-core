from __future__ import annotations

import os
import subprocess


BUCKET = os.getenv("OPPORTUNITY_SCAN_BUCKET", "intraday")
TIMEFRAME = os.getenv("OPPORTUNITY_SCAN_TIMEFRAME", "M5")
TOP_N = int(os.getenv("MOEX_TOP_UNIVERSE_LIMIT", "30"))


SQL = f"""
insert into moex_top_universe (
    symbol,
    board,
    asset_class,
    short_name,
    last_price,
    change_pct,
    value_today,
    volume_today,
    intraday_range_pct,
    turnover_score,
    volatility_score,
    volume_score,
    total_score,
    reason,
    source,
    calculated_at
)
with latest_scan as (
    select max(scan_ts) as scan_ts
    from volatility_scan_results
    where bucket = '{BUCKET}'
      and timeframe = '{TIMEFRAME}'
),
src as (
    select v.*
    from volatility_scan_results v
    join latest_scan l on l.scan_ts = v.scan_ts
    where v.bucket = '{BUCKET}'
      and v.timeframe = '{TIMEFRAME}'
      and v.symbol like '%@MISX'
),
scored as (
    select
        symbol,
        'TQBR' as board,
        'EQUITY' as asset_class,
        coalesce(raw_json->>'short_name', symbol) as short_name,
        coalesce((raw_json->>'last_price')::numeric, 0) as last_price,
        coalesce((raw_json->>'change_pct')::numeric, 0) as change_pct,
        coalesce(turnover, 0) as value_today,
        coalesce((raw_json->>'volume')::numeric, 0) as volume_today,
        coalesce(nullif(atr_pct, 0), (raw_json->>'range_pct')::numeric, 0) as intraday_range_pct,

        least(coalesce(turnover, 0) / 1000000000.0, 1.0) as turnover_score,
        least(coalesce(nullif(atr_pct, 0), (raw_json->>'range_pct')::numeric, 0) / 0.05, 1.0) as volatility_score,
        least(coalesce((raw_json->>'rvol')::numeric, 0) / 5.0, 1.0) as volume_score,

        (
            0.40 * least(coalesce(turnover, 0) / 1000000000.0, 1.0)
          + 0.35 * least(coalesce(nullif(atr_pct, 0), (raw_json->>'range_pct')::numeric, 0) / 0.05, 1.0)
          + 0.25 * least(coalesce((raw_json->>'rvol')::numeric, 0) / 5.0, 1.0)
        ) as total_score,

        'turnover=' || round(coalesce(turnover, 0)::numeric, 2) ||
        ';atr_pct=' || round(coalesce(nullif(atr_pct, 0), (raw_json->>'range_pct')::numeric, 0)::numeric, 6) ||
        ';rvol=' || round(coalesce((raw_json->>'rvol')::numeric, 0)::numeric, 4) as reason

    from src
    where symbol is not null
)
select
    symbol,
    board,
    asset_class,
    short_name,
    last_price,
    change_pct,
    value_today,
    volume_today,
    intraday_range_pct,
    turnover_score,
    volatility_score,
    volume_score,
    total_score,
    reason,
    'volatility_scan_results',
    now()
from scored
order by total_score desc
limit {TOP_N};
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
    print("OK: moex top universe updated from volatility_scan_results")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
