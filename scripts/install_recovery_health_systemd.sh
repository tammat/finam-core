#!/usr/bin/env bash
set -euo pipefail

sudo cp systemd/finam-recovery-health.service /etc/systemd/system/finam-recovery-health.service
sudo cp systemd/finam-recovery-health.timer /etc/systemd/system/finam-recovery-health.timer

sudo systemctl daemon-reload
sudo systemctl enable finam-recovery-health.timer
sudo systemctl start finam-recovery-health.timer

echo "RECOVERY_HEALTH_SYSTEMD_INSTALLED"
echo "Timer:  systemctl status finam-recovery-health.timer --no-pager"
echo "Run:    sudo systemctl start finam-recovery-health.service"
echo "Logs:   journalctl -u finam-recovery-health.service -n 50 --no-pager"
