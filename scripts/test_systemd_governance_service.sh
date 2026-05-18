#!/usr/bin/env bash
set -euo pipefail

systemctl cat finam-governance.service >/dev/null
systemctl is-enabled finam-governance.service >/dev/null
systemctl is-active finam-governance.service >/dev/null

echo "OK: finam-governance systemd service active"
