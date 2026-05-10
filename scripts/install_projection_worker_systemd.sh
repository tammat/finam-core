#!/usr/bin/env bash
set -euo pipefail

sudo cp systemd/finam-projection-worker.service /etc/systemd/system/finam-projection-worker.service
sudo systemctl daemon-reload
sudo systemctl enable finam-projection-worker.service

echo "PROJECTION_WORKER_SYSTEMD_INSTALLED"
echo "Start:  sudo systemctl start finam-projection-worker.service"
echo "Logs:   journalctl -u finam-projection-worker.service -f"
