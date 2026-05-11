#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f deploy/systemd/finam-protective-recovery-check.service
test -f deploy/systemd/finam-protective-recovery-check.timer

grep -q "Description=Finam Core Protective Order Recovery Check" deploy/systemd/finam-protective-recovery-check.service
grep -q "Type=oneshot" deploy/systemd/finam-protective-recovery-check.service
grep -q "TimeoutStartSec=30" deploy/systemd/finam-protective-recovery-check.service
grep -q "User=finam" deploy/systemd/finam-protective-recovery-check.service
grep -q "EnvironmentFile=/opt/finam-core/deploy/env/.env" deploy/systemd/finam-protective-recovery-check.service
grep -q "src/scripts/check_protective_order_recovery.py" deploy/systemd/finam-protective-recovery-check.service

grep -q "OnUnitActiveSec=1min" deploy/systemd/finam-protective-recovery-check.timer
grep -q "WantedBy=timers.target" deploy/systemd/finam-protective-recovery-check.timer

python -m py_compile src/scripts/check_protective_order_recovery.py
python -m py_compile src/finam_core/reconciliation/protective_order_recovery_check.py

echo "SYSTEMD_PROTECTIVE_RECOVERY_CHECK_TIMER_TEST_OK"
