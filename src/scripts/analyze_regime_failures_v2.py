from __future__ import annotations

import os
import subprocess


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
    sql = """
select
  analytics_symbol,
  strategy,
  regime,
  source,
  confidence_bucket,
  fills,
  signed_cashflow,
  avg_signed_cashflow,
  avg_confidence,
  case
    when fills < 3 then 'NO_DATA'
    when signed_cashflow < 0 and avg_signed_cashflow < 0 then 'FAILURE_ZONE'
    when signed_cashflow >= 0 and avg_signed_cashflow >= 0 then 'OK_ZONE'
    else 'MIXED_ZONE'
  end as failure_status
from analytics_strategy_regime_attribution_v2
order by signed_cashflow asc;
"""
    print(run_psql(sql))
    print("OK: RegimeFailureAnalyzer v2 completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
