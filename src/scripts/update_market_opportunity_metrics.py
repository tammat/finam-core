from __future__ import annotations

import os
import subprocess


BUCKET = os.getenv("OPPORTUNITY_SCAN_BUCKET", "intraday")
TIMEFRAME = os.getenv("OPPORTUNITY_SCAN_TIMEFRAME", "M5")


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
)
select
    symbol,
    'EQUITY' as asset_class,
    coalesce(nullif(atr_pct, 0), (raw_json->>'range_pct')::numeric, 0) as atr_pct,
    coalesce((raw_json->>'rvol')::numeric, 0) as rvol,
    coalesce(turnover, 0) as turnover,
    coalesce((raw_json->>'spread_pct')::numeric, 0) as spread_pct,
    coalesce(raw_json->>'regime', 'unknown_trend_unknown_vol') as regime,
    coalesce(raw_json->>'reason', 'passed') = 'passed' as is_tradeable,
    raw_json || jsonb_build_object(
        'source', 'volatility_scan_results',
        'bucket', bucket,
        'timeframe', timeframe,
        'scan_ts', scan_ts,
        'rank', rank,
        'score', score
    ) as raw,
    now() as calculated_at
from src
where symbol is not null;
"""
    print(run_psql(sql))
    print("OK: market opportunity metrics updated from volatility_scan_results")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
