#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

test -f infra/finam-equity-market-bars.service
test -f infra/finam-equity-market-bars.timer

grep -q "backfill_equity_watch_market_bars_v1.py" infra/finam-equity-market-bars.service
grep -q "NoNewPrivileges=true" infra/finam-equity-market-bars.service
grep -q "Europe/Moscow" infra/finam-equity-market-bars.timer
grep -q "10:00/15:00" infra/finam-equity-market-bars.timer

if grep -Eiq "order|execution|runtime_allow=1|execution_enabled=1" infra/finam-equity-market-bars.service
then
  echo "EQUITY_AUTORUN_SAFETY_FAIL"
  exit 1
fi

echo TEST_MARKET_DATA_EQUITY_AUTORUN_V1_OK
