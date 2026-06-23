#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== INSTALL_RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_TIMER_V1 ==="

sudo cp infra/systemd/finam-rs-bottom-runtime-live-collector.service /etc/systemd/system/
sudo cp infra/systemd/finam-rs-bottom-runtime-live-collector.timer /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now finam-rs-bottom-runtime-live-collector.timer

sudo systemctl list-timers --all | grep finam-rs-bottom-runtime-live-collector || true

echo "INSTALL_RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_TIMER_V1_OK"
