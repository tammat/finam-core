#!/usr/bin/env bash
set -euo pipefail

systemctl cat finam-paper-runtime.service >/dev/null
systemctl is-enabled finam-paper-runtime.service >/dev/null
systemctl is-active finam-paper-runtime.service >/dev/null

echo "OK: finam-paper-runtime systemd service active"
