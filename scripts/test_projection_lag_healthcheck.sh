#!/usr/bin/env bash
set -euo pipefail

test -x scripts/check_projection_lag.sh

grep -q "event_store" scripts/check_projection_lag.sh
grep -q "projection_checkpoints" scripts/check_projection_lag.sh
grep -q "PROJECTION_LAG_OK" scripts/check_projection_lag.sh
grep -q "PROJECTION_LAG_FAIL" scripts/check_projection_lag.sh

echo "PROJECTION_LAG_HEALTHCHECK_SCRIPT_OK"
