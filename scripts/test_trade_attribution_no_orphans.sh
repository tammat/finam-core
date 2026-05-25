#!/usr/bin/env bash
set -euo pipefail

ORPHANS=$(psql "$DATABASE_URL" -t -A -c "
SELECT COUNT(*)
FROM trade_attribution_v2 a
WHERE NOT EXISTS (
  SELECT 1
  FROM closed_trade_chains_v2 c
  WHERE c.id = a.closed_trade_id
);
")

if [ "$ORPHANS" != "0" ]; then
  echo "ERROR: orphan trade_attribution_v2 rows count=$ORPHANS"
  exit 1
fi

echo "TRADE_ATTRIBUTION_NO_ORPHANS_OK"
