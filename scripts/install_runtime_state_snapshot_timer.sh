#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

sudo cp "$ROOT_DIR/systemd/runtime-state-snapshot.service" /etc/systemd/system/
sudo cp "$ROOT_DIR/systemd/runtime-state-snapshot.timer" /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable runtime-state-snapshot.timer
sudo systemctl restart runtime-state-snapshot.timer

echo "OK: runtime-state-snapshot timer installed"
sudo systemctl status runtime-state-snapshot.timer --no-pager
