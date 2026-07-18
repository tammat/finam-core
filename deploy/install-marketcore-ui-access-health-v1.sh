#!/usr/bin/env bash
set -euo pipefail

install -m 0644 deploy/systemd/marketcore-ui-access-health.service /etc/systemd/system/
install -m 0644 deploy/systemd/marketcore-ui-access-health.timer /etc/systemd/system/
install -m 0644 deploy/systemd/marketcore-ui-access-recover.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now marketcore-ui-access-health.timer
systemctl start marketcore-ui-access-health.service
