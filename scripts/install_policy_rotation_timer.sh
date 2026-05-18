#!/usr/bin/env bash
set -euo pipefail

sudo cp systemd/policy-rotation.service /etc/systemd/system/
sudo cp systemd/policy-rotation.timer /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable policy-rotation.timer
sudo systemctl restart policy-rotation.timer

echo "OK: policy rotation timer installed"

sudo systemctl status policy-rotation.timer --no-pager
