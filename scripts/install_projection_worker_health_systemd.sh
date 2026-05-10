#!/usr/bin/env bash
set -euo pipefail

sudo cp systemd/finam-projection-worker-health.service /etc/systemd/system/finam-projection-worker-health.service
sudo cp systemd/finam-projection-worker-health.timer /etc/systemd/system/finam-projection-worker-health.timer

sudo systemctl daemon-reload
sudo systemctl enable finam-projection-worker-health.timer
sudo systemctl start finam-projection-worker-health.timer

echo "PROJECTION_WORKER_HEALTH_SYSTEMD_INSTALLED"
echo "Timer:  systemctl status finam-projection-worker-health.timer --no-pager"
echo "Run:    sudo systemctl start finam-projection-worker-health.service"
echo "Logs:   journalctl -u finam-projection-worker-health.service -n 50 --no-pager"
