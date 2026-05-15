#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from decimal import Decimal
from uuid import uuid4

from finam_core.storage.postgres_logger import PostgresLogger
from finam_core.contracts.contract_identity_resolver import ContractIdentityResolver

logger = PostgresLogger()

trade_id = f"smoke-{uuid4().hex[:12]}"

identity = ContractIdentityResolver.resolve("BRN6@RTSX")

payload = {
    "signal_id": f"sig-{trade_id}",
    "strategy": "BR_CONSERVATIVE_BREAKOUT",
    "source": "strategy_attribution_smoke",
    "confidence": 0.91,
    "regime": "TREND",
    "continuous_symbol": identity.continuous,
    "root_symbol": identity.root,
    "futures_month_code": identity.month_code,
    "futures_year_code": identity.year_code,
    "venue": identity.venue,
    "is_futures": identity.is_futures,
    "attribution_version": "strategy_attribution_v1",
}

logger.log_fill(
    symbol="BRN6@RTSX",
    side="BUY",
    qty=1,
    price=Decimal("108.55"),
    trade_id=trade_id,
    execution_type="paper",
    commission=Decimal("0.054"),
    payload=payload,
)

print("OK: strategy attribution smoke fill logged")
print(payload)
PY

psql "$DATABASE_URL" -P pager=off -c "
select
  ts at time zone 'Europe/Moscow' as ts_msk,
  symbol,
  payload->>'strategy' as strategy,
  payload->>'confidence' as confidence,
  payload->>'continuous_symbol' as continuous_symbol,
  payload->>'attribution_version' as attribution_version,
  payload->>'source' as source
from trades
where payload->>'source'='strategy_attribution_smoke'
order by ts desc
limit 5;
"
