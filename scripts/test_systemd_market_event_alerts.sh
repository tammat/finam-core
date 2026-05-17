#!/usr/bin/env bash
set -euo pipefail

test -f deploy/systemd/finam-market-event-alerts.service
test -f deploy/systemd/finam-market-event-alerts.timer

grep -q "send_market_event_calendar_alerts_telegram.py" deploy/systemd/finam-market-event-alerts.service
grep -q "User=finam" deploy/systemd/finam-market-event-alerts.service
grep -q "EnvironmentFile=/opt/finam-core/.env" deploy/systemd/finam-market-event-alerts.service
grep -q "OnUnitActiveSec=15min" deploy/systemd/finam-market-event-alerts.timer
grep -q "Persistent=true" deploy/systemd/finam-market-event-alerts.timer

echo "OK: systemd market event alerts timer"
