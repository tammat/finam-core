#!/usr/bin/env bash
set -euo pipefail

test -x scripts/check_projection_worker_health.sh

grep -q "systemctl is-active" scripts/check_projection_worker_health.sh
grep -q "projection_checkpoints" scripts/check_projection_worker_health.sh
grep -q "portfolio_projection" scripts/check_projection_worker_health.sh
grep -q "PROJECTION_WORKER_HEALTH_OK" scripts/check_projection_worker_health.sh
grep -q "PROJECTION_WORKER_HEALTH_FAIL" scripts/check_projection_worker_health.sh

echo "PROJECTION_WORKER_HEALTHCHECK_SCRIPT_OK"
