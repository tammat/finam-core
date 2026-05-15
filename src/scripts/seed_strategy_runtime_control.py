from __future__ import annotations

import os
import subprocess


SEED_ROWS = [
    ("OZON@MISX", "TREND_PULLBACK_EQUITY"),
    ("SFIN@MISX", "TREND_PULLBACK_EQUITY"),
    ("LKOH@MISX", "MEAN_REVERSION_EQUITY"),
    ("NVTK@MISX", "MEAN_REVERSION_EQUITY"),
    ("T@MISX", "TREND_PULLBACK_EQUITY"),
    ("SBER@MISX", "TREND_PULLBACK_EQUITY"),
    ("SBERP@MISX", "TREND_PULLBACK_EQUITY"),
    ("GAZP@MISX", "MEAN_REVERSION_EQUITY"),
    ("BRM6@RTSX", "BR_CONSERVATIVE_BREAKOUT"),
    ("USDRUBF@RTSX", "USDRUB_REGIME"),
    ("NGH6@RTSX", "NG_VOLATILITY_BREAKOUT"),
]


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
    values_sql = ",\n".join(
        f"('{symbol}', '{strategy}', 'WATCH', false, true, 0.0, 'seed_runtime_control_no_data', now())"
        for symbol, strategy in SEED_ROWS
    )

    sql = f"""
insert into strategy_runtime_control (
  symbol, strategy, status, allow_trade, watch_only,
  risk_multiplier, reason, updated_at
)
values
{values_sql}
on conflict (symbol, strategy) do nothing;

select symbol, strategy, status, allow_trade, watch_only, risk_multiplier, reason
from strategy_runtime_control
where reason = 'seed_runtime_control_no_data'
order by symbol, strategy;
"""

    print(run_psql(sql))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
