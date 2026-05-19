#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

sudo cp "$ROOT_DIR/systemd/runtime-supervisor.service" /etc/systemd/system/
sudo cp "$ROOT_DIR/systemd/runtime-supervisor.timer" /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable runtime-supervisor.timer
sudo systemctl restart runtime-supervisor.timer

echo "OK: runtime-supervisor timer installed"
sudo systemctl status runtime-supervisor.timer --no-pager
