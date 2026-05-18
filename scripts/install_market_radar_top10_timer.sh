#!/usr/bin/env bash
set -euo pipefail

sudo cp systemd/market-radar-top10.service /etc/systemd/system/
sudo cp systemd/market-radar-top10.timer /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable market-radar-top10.timer
sudo systemctl restart market-radar-top10.timer

echo "OK: market radar top10 timer installed"
sudo systemctl status market-radar-top10.timer --no-pager
