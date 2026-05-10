#!/usr/bin/env bash
set -euo pipefail

test -f systemd/finam-recovery-health.service
test -f systemd/finam-recovery-health.timer

grep -q "Finam Core Recovery Orchestrator Healthcheck" systemd/finam-recovery-health.service
grep -q "Type=oneshot" systemd/finam-recovery-health.service
grep -q "check_recovery_orchestrator.sh" systemd/finam-recovery-health.service

grep -q "OnBootSec=60" systemd/finam-recovery-health.timer
grep -q "OnUnitActiveSec=60" systemd/finam-recovery-health.timer
grep -q "timers.target" systemd/finam-recovery-health.timer

test -x scripts/install_recovery_health_systemd.sh

echo "RECOVERY_HEALTH_SYSTEMD_OK"
