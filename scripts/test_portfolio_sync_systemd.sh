#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f systemd/finam-portfolio-sync.service
test -f systemd/finam-portfolio-sync.timer
test -x scripts/install_portfolio_sync_systemd.sh
test -x scripts/sync_real_portfolio_from_finam.sh

grep -q "Finam Core Real Portfolio Sync" systemd/finam-portfolio-sync.service
grep -q "OnUnitActiveSec=60" systemd/finam-portfolio-sync.timer

echo "PORTFOLIO_SYNC_SYSTEMD_OK"
