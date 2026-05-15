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
select id, symbol, coalesce(payload->>'strategy', '') as strategy
from trades
where origin='paper'
order by id;
""").strip().splitlines()

    updated = 0

    for line in rows[1:]:
        line = line.strip()
        if not line or "\t" not in line:
            continue

        parts = line.split("\t")
        if len(parts) < 3:
            continue

        trade_id, symbol, strategy = parts[0], parts[1], parts[2]
        identity = ContractIdentityResolver.resolve(symbol)

        patch = {
            "root_symbol": identity.root,
            "continuous_symbol": identity.continuous if identity.is_futures else symbol,
            "futures_month_code": identity.month_code,
            "futures_year_code": identity.year_code,
            "venue": identity.venue,
            "is_futures": identity.is_futures,
            "confidence": 1.0,
            "attribution_version": "strategy_attribution_backfill_v1",
        }

        if strategy:
            patch["strategy"] = strategy

        patch_json = json.dumps(patch, ensure_ascii=False)

        run_psql(f"""
update trades
set payload = coalesce(payload, '{{}}'::jsonb) || '{patch_json}'::jsonb
where id = {int(trade_id)}
  and (
    payload->>'attribution_version' is null
    or payload->>'confidence' is null
    or payload->>'continuous_symbol' is null
    or payload->>'continuous_symbol' in ('PLZL','OZO_CONT','SFI_CONT')
  );
""")
        updated += 1

    print(f"OK: strategy attribution backfill processed trades={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
