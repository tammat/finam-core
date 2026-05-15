from __future__ import annotations

import os
import subprocess

from finam_core.contracts.runtime_symbol_mapper import RuntimeSymbolMapper
from finam_core.strategy.symbol_strategy_map import SYMBOL_STRATEGY_MAP


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
    values = []

    for raw_symbol, strategy in sorted(SYMBOL_STRATEGY_MAP.items()):
        control_symbol = RuntimeSymbolMapper.runtime_symbol(raw_symbol)

        values.append(
            "('{symbol}', '{strategy}', 'WATCH', false, true, 0.0, "
            "'seed_from_strategy_map_no_data', now())".format(
                symbol=control_symbol.replace("'", "''"),
                strategy=str(strategy).replace("'", "''"),
            )
        )

    if not values:
        print("NO SYMBOL_STRATEGY_MAP rows")
        return 0

    sql = f"""
insert into strategy_runtime_control (
  symbol, strategy, status, allow_trade, watch_only,
  risk_multiplier, reason, updated_at
)
values
  {",".join(values)}
on conflict (symbol, strategy) do nothing;
"""

    print(run_psql(sql))
    print(f"OK: seeded runtime-control rows={len(values)} from SYMBOL_STRATEGY_MAP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
