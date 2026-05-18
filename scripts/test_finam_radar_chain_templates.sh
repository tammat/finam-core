#!/usr/bin/env bash
set -euo pipefail

test -f systemd/finam-radar-chain.service
test -f systemd/finam-radar-chain.timer

grep -q "run_market_radar.py" \
  systemd/finam-radar-chain.service

grep -q "OnUnitActiveSec=15min" \
  systemd/finam-radar-chain.timer

grep -q "systemctl enable finam-radar-chain.timer" \
  scripts/install_finam_radar_chain_timer.sh

echo "OK: finam radar chain templates"
