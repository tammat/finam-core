from __future__ import annotations

import json
import os
import subprocess

from finam_core.contracts.contract_identity_resolver import ContractIdentityResolver


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
    payload->>'continuous_symbol' is null
    or payload->>'continuous_symbol' = ''
  )
order by id;
""").strip().splitlines()

    if len(rows) <= 1:
        print("OK: no trades to backfill")
        return 0

    updated = 0

    for line in rows[1:]:
        line = line.strip()

        if not line:
            continue

        if "\t" not in line:
            continue

        trade_id, symbol = line.split("\t", 1)
        identity = ContractIdentityResolver.resolve(symbol)

        patch = {
            "root_symbol": identity.root,
            "continuous_symbol": identity.continuous,
            "futures_month_code": identity.month_code,
            "futures_year_code": identity.year_code,
            "venue": identity.venue,
            "is_futures": identity.is_futures,
        }

        patch_json = json.dumps(patch, ensure_ascii=False)

        run_psql(f"""
update trades
set payload = payload || '{patch_json}'::jsonb
where id = {int(trade_id)};
""")
        updated += 1

    print(f"OK: backfilled contract identity for trades={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
