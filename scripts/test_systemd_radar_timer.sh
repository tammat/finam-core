#!/usr/bin/env bash
set -euo pipefail

systemctl cat finam-radar.service >/dev/null
systemctl cat finam-radar.timer >/dev/null

echo "SYSTEMD_RADAR_TIMER_OK"
