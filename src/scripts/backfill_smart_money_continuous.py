from __future__ import annotations

import os
import subprocess


SQL = """
insert into smart_money_feature_events (
    ts,
    symbol,
    rvol,
    tick_velocity,
    price_velocity,
    range_pct,
    absorption_score,
    sweep_reclaim_score,
    impulse_score,
    smart_money_score,
    label,
    raw_json
)
select
    now(),
    'BR_CONT',
    rvol,
    tick_velocity,
    price_velocity,
    range_pct,
    absorption_score,
    sweep_reclaim_score,
    impulse_score,
    smart_money_score,
    label,
    raw_json || jsonb_build_object(
        'source_symbol', symbol,
        'continuous_symbol', 'BR_CONT',
        'backfill_source', 'backfill_smart_money_continuous'
    )
from smart_money_feature_events
where symbol in ('BRM6@RTSX', 'BRN6@RTSX', 'BRQ6@RTSX')
order by ts desc
limit 1;
"""


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL_NOT_SET")

    result = subprocess.run(
        ["psql", database_url, "-P", "pager=off", "-v", "ON_ERROR_STOP=1", "-c", SQL],
        text=True,
        capture_output=True,
        check=True,
    )

    print(result.stdout)
    print("OK: smart money continuous backfill completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
