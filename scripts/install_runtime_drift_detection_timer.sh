#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

sudo cp "$ROOT_DIR/systemd/runtime-drift-detection.service" /etc/systemd/system/
sudo cp "$ROOT_DIR/systemd/runtime-drift-detection.timer" /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable runtime-drift-detection.timer
sudo systemctl restart runtime-drift-detection.timer

echo "OK: runtime drift detection timer installed"
