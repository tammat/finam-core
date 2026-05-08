#!/usr/bin/env bash
set -euo pipefail

echo "=== FINAM TIMERS ==="
systemctl list-timers | grep finam || true

echo
echo "=== TIMER STATUS ==="
systemctl is-enabled finam-position-sync.timer
systemctl is-enabled finam-market-radar.timer
systemctl is-enabled finam-volatility-scan.timer

systemctl is-active finam-position-sync.timer
systemctl is-active finam-market-radar.timer
systemctl is-active finam-volatility-scan.timer

echo
echo "FINAM_SERVICES_CHECK_OK"
