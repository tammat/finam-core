from __future__ import annotations

import os
import subprocess


SQL = """
with src as (
    select
        dw.symbol,
        coalesce(nullif(dw.strategy, ''), 'default') as strategy
    from dynamic_watchlist dw
    where dw.is_active = true
      and dw.symbol is not null
      and coalesce(dw.strategy, '') <> ''
),
updated as (
    update strategy_runtime_control rtc
    set
        status = 'WATCH',
        risk_multiplier = 1.0,
        reason = 'runtime_control_seed_from_dynamic_universe',
        updated_at = now()
    from src
    where rtc.symbol = src.symbol
      and rtc.strategy = src.strategy
    returning rtc.symbol, rtc.strategy
)
insert into strategy_runtime_control (
    symbol,
    strategy,
    status,
    risk_multiplier,
    reason,
    updated_at
)
select
    src.symbol,
    src.strategy,
    'WATCH',
    1.0,
    'runtime_control_seed_from_dynamic_universe',
    now()
from src
where not exists (
    select 1
    from updated u
    where u.symbol = src.symbol
      and u.strategy = src.strategy
);

select
    symbol,
    strategy,
    status,
    risk_multiplier,
    reason,
    updated_at
from strategy_runtime_control
where reason = 'runtime_control_seed_from_dynamic_universe'
order by updated_at desc, symbol;
"""


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    result = subprocess.run(
        [
            "psql",
            database_url,
            "-P",
            "pager=off",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            SQL,
        ],
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        return result.returncode

    print(result.stdout)
    print("OK: runtime control updated from dynamic universe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
