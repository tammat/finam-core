#!/usr/bin/env bash
set -euo pipefail

test -x scripts/check_production_health.sh

grep -q "PRODUCTION_HEALTH_OK" scripts/check_production_health.sh
grep -q "PRODUCTION_HEALTH_FAIL" scripts/check_production_health.sh
grep -q "check_projection_lag.sh" scripts/check_production_health.sh
grep -q "check_recovery_orchestrator.sh" scripts/check_production_health.sh
grep -q "check_dlq_health.sh" scripts/check_production_health.sh
grep -q "PersistentKillSwitch" scripts/check_production_health.sh

echo "PRODUCTION_HEALTHCHECK_SCRIPT_OK"
