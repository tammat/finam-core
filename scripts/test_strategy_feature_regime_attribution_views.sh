#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_strategy_feature_regime_attribution_views.sql >/dev/null

psql "$DATABASE_URL" -P pager=off -c "
select
  analytics_symbol,
  strategy,
  regime,
  source,
  confidence_bucket,
  fills,
  signed_cashflow,
  avg_confidence
from analytics_strategy_regime_attribution_v2
order by signed_cashflow asc
limit 30;
"

echo "OK: strategy feature/regime attribution view"
