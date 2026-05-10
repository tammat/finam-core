#!/usr/bin/env bash
set -euo pipefail

test -x scripts/check_recovery_orchestrator.sh

grep -q "RecoveryOrchestrator" scripts/check_recovery_orchestrator.sh
grep -q "RECOVERY_ORCHESTRATOR_HEALTH_OK" scripts/check_recovery_orchestrator.sh
grep -q "RECOVERY_ORCHESTRATOR_HEALTH_FAIL" scripts/check_recovery_orchestrator.sh

echo "RECOVERY_ORCHESTRATOR_HEALTHCHECK_OK"
