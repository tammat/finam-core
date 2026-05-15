from __future__ import annotations

import json
import os
import subprocess

from finam_core.contracts.contract_identity_resolver import ContractIdentityResolver
from finam_core.strategy.symbol_strategy_map import SYMBOL_STRATEGY_MAP, DEFAULT_STRATEGY


def run_psql(sql: str) -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    result = subprocess.run(
        ["psql", database_url, "-P", "pager=off", "-A", "-F", "\t", "-v", "ON_ERROR_STOP=1", "-c", sql],
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


def main() -> int:
    rows = run_psql("""
select id, symbol
from trades
where origin='paper'
  and (
    payload->>'strategy' is null
    or payload->>'strategy' = ''
    or payload->>'confidence' is null
    or payload->>'attribution_version' is null
  )
order by id;
""").strip().splitlines()

    updated = 0

    for line in rows[1:]:
        if not line.strip() or "\t" not in line:
            continue

        trade_id, symbol = line.split("\t", 1)
        strategy = SYMBOL_STRATEGY_MAP.get(symbol, DEFAULT_STRATEGY)
        identity = ContractIdentityResolver.resolve(symbol)

        patch = {
            "strategy": strategy,
            "root_symbol": identity.root,
            "continuous_symbol": identity.continuous if identity.is_futures else symbol,
            "futures_month_code": identity.month_code,
            "futures_year_code": identity.year_code,
            "venue": identity.venue,
            "is_futures": identity.is_futures,
            "confidence": 1.0,
            "attribution_version": "strategy_attribution_map_backfill_v1",
        }

        patch_json = json.dumps(patch, ensure_ascii=False)

        run_psql(f"""
update trades
set payload = coalesce(payload, '{{}}'::jsonb) || '{patch_json}'::jsonb
where id = {int(trade_id)};
""")
        updated += 1

    print(f"OK: map attribution backfill updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
