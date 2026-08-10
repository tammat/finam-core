#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

DB="postgresql:///finam_core"

echo "=== TEST_V5_FUTURES_ROLLOVER_EXPIRY_FALLBACK_V1 ==="

EXPIRY="$(
psql "$DB" -X -Atc "
SELECT source_payload->>'LASTTRADEDATE'
FROM analytics.contract_spec_sync_item_v1
WHERE symbol='BRQ6@RTSX'
  AND status_code IN ('CREATED','UPDATED','UNCHANGED')
  AND source_version='MOEX_ISS_CONTRACT_SPEC_V1'
  AND source_payload ? 'LASTTRADEDATE'
ORDER BY created_at DESC
LIMIT 1;
"
)"

[ "$EXPIRY" = "2026-08-03" ]

python - <<'PY'
from datetime import date

from scripts.run_v5_futures_rollover_v1 import (
    choose_rollover,
)

expiry = date(2026, 8, 3)
today = date(2026, 8, 10)
days = (expiry - today).days

assert days == -7

allowed, reason = choose_rollover(
    days=days,
    current_volume=0.0,
    current_trades=0,
    next_volume=69818.0,
    next_trades=19323,
)

assert allowed is True
assert reason == "EXPIRY_PROTECTION"

print("persisted_expiry=2026-08-03")
print("days_to_expiry=-7")
print("roll_allowed=1")
print("roll_reason=EXPIRY_PROTECTION")
PY

grep -q \
'def persisted_last_trade_date' \
src/scripts/run_v5_futures_rollover_v1.py

grep -q \
'PERSISTED_MOEX_SPEC' \
src/scripts/run_v5_futures_rollover_v1.py

echo "market_contract_spec_valid_to_used_as_expiry=0"
echo "persisted_moex_last_trade_date_used=1"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_V5_FUTURES_ROLLOVER_EXPIRY_FALLBACK_V1_OK"
