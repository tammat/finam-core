#!/usr/bin/env bash
set -euo pipefail

test -f systemd/finam-projection-worker-health.service
test -f systemd/finam-projection-worker-health.timer

grep -q "Finam Core Projection Worker Healthcheck" systemd/finam-projection-worker-health.service
grep -q "Type=oneshot" systemd/finam-projection-worker-health.service
grep -q "check_projection_worker_health.sh" systemd/finam-projection-worker-health.service

grep -q "OnBootSec=30" systemd/finam-projection-worker-health.timer
grep -q "OnUnitActiveSec=60" systemd/finam-projection-worker-health.timer
grep -q "timers.target" systemd/finam-projection-worker-health.timer

test -x scripts/install_projection_worker_health_systemd.sh

echo "PROJECTION_WORKER_HEALTH_SYSTEMD_OK"
