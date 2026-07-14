#!/bin/bash
set -euo pipefail

ROOT=/opt/finam-core
USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"

install -d -m 0755 "${USER_SYSTEMD_DIR}"
install -m 0644 \
  "${ROOT}/deploy/systemd/user/finam-microstructure-health.service" \
  "${USER_SYSTEMD_DIR}/finam-microstructure-health.service"
install -m 0644 \
  "${ROOT}/deploy/systemd/user/finam-microstructure-health.timer" \
  "${USER_SYSTEMD_DIR}/finam-microstructure-health.timer"

systemctl --user daemon-reload
systemctl --user enable --now finam-microstructure-health.timer
systemctl --user is-active --quiet finam-microstructure-health.timer
