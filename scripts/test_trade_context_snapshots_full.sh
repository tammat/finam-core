#!/usr/bin/env bash
set -euo pipefail

BAD_COUNT=$(psql "$DATABASE_URL" -t -A -c "
SELECT COUNT(*)
FROM trade_context_snapshots
WHERE symbol='BRM6@RTSX'
  AND strategy='BR_CONSERVATIVE_BREAKOUT'
  AND context_quality <> 'FULL';
")

if [ "$BAD_COUNT" != "0" ]; then
  echo "ERROR: partial trade_context_snapshots count=$BAD_COUNT"
  exit 1
fi

echo "TRADE_CONTEXT_SNAPSHOTS_FULL_OK"
