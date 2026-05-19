#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

sudo cp "$ROOT_DIR/systemd/runtime-anomaly-correlation.service" /etc/systemd/system/
sudo cp "$ROOT_DIR/systemd/runtime-anomaly-correlation.timer" /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable runtime-anomaly-correlation.timer
sudo systemctl restart runtime-anomaly-correlation.timer

echo "OK: runtime anomaly correlation timer installed"
