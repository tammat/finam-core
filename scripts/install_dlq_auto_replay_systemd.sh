#!/usr/bin/env bash
set -euo pipefail

sudo cp systemd/finam-dlq-auto-replay.service /etc/systemd/system/finam-dlq-auto-replay.service
sudo cp systemd/finam-dlq-auto-replay.timer /etc/systemd/system/finam-dlq-auto-replay.timer

sudo systemctl daemon-reload
sudo systemctl enable finam-dlq-auto-replay.timer
sudo systemctl start finam-dlq-auto-replay.timer

echo "DLQ_AUTO_REPLAY_SYSTEMD_INSTALLED"
echo "Timer:  systemctl status finam-dlq-auto-replay.timer --no-pager"
echo "Run:    sudo systemctl start finam-dlq-auto-replay.service"
echo "Logs:   journalctl -u finam-dlq-auto-replay.service -n 50 --no-pager"
