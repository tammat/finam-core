#!/usr/bin/env bash
set -euo pipefail

test -f deploy/systemd/finam-alerts-telegram.service
test -f deploy/systemd/finam-alerts-telegram.timer

grep -q "send_grafana_alerts_telegram.py" deploy/systemd/finam-alerts-telegram.service
grep -q "TELEGRAM_ALERT_COOLDOWN_MIN=30" deploy/systemd/finam-alerts-telegram.service
grep -q "OnUnitActiveSec=2min" deploy/systemd/finam-alerts-telegram.timer
grep -q "Persistent=true" deploy/systemd/finam-alerts-telegram.timer

echo "OK: systemd telegram alerts timer"
