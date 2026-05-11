#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

sudo cp systemd/finam-portfolio-sync.service /etc/systemd/system/finam-portfolio-sync.service
sudo cp systemd/finam-portfolio-sync.timer /etc/systemd/system/finam-portfolio-sync.timer

sudo systemctl daemon-reload
sudo systemctl enable finam-portfolio-sync.timer
sudo systemctl start finam-portfolio-sync.timer

echo "PORTFOLIO_SYNC_SYSTEMD_INSTALLED"
