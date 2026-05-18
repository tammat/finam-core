#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

sudo cp \
  "$ROOT_DIR/systemd/finam-radar-chain.service" \
  /etc/systemd/system/

sudo cp \
  "$ROOT_DIR/systemd/finam-radar-chain.timer" \
  /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable finam-radar-chain.timer
sudo systemctl restart finam-radar-chain.timer

echo "OK: finam-radar-chain timer installed"
