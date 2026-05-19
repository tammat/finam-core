#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

sudo cp "$ROOT_DIR/systemd/runtime-operational-dashboard.service" /etc/systemd/system/
sudo cp "$ROOT_DIR/systemd/runtime-operational-dashboard.timer" /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable runtime-operational-dashboard.timer
sudo systemctl restart runtime-operational-dashboard.timer

echo "OK: runtime operational dashboard timer installed"
