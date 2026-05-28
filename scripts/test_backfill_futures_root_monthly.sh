#!/usr/bin/env bash
set -euo pipefail

test -x scripts/backfill_futures_root_monthly.sh
grep -q -- "--roots" scripts/backfill_futures_root_monthly.sh
grep -q -- "--max-contracts" scripts/backfill_futures_root_monthly.sh
grep -q "ROOT_MONTHLY_BACKFILL_CHUNK" scripts/backfill_futures_root_monthly.sh

echo "BACKFILL_FUTURES_ROOT_MONTHLY_TEST_OK"
