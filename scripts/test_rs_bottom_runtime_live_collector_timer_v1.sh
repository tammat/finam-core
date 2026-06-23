#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_TIMER_V1 ==="

test -f infra/systemd/finam-rs-bottom-runtime-live-collector.service
test -f infra/systemd/finam-rs-bottom-runtime-live-collector.timer
test -x scripts/install_rs_bottom_runtime_live_collector_timer_v1.sh

grep -q "Type=oneshot" infra/systemd/finam-rs-bottom-runtime-live-collector.service
grep -q "run_rs_bottom_runtime_live_collector_v1.py" infra/systemd/finam-rs-bottom-runtime-live-collector.service
grep -q "OnUnitActiveSec=5min" infra/systemd/finam-rs-bottom-runtime-live-collector.timer
grep -q "Persistent=true" infra/systemd/finam-rs-bottom-runtime-live-collector.timer

sudo systemd-analyze verify \
  infra/systemd/finam-rs-bottom-runtime-live-collector.service \
  infra/systemd/finam-rs-bottom-runtime-live-collector.timer

bash scripts/install_rs_bottom_runtime_live_collector_timer_v1.sh

sudo systemctl is-enabled finam-rs-bottom-runtime-live-collector.timer
sudo systemctl is-active finam-rs-bottom-runtime-live-collector.timer

sudo systemctl start finam-rs-bottom-runtime-live-collector.service
sleep 2

journalctl -u finam-rs-bottom-runtime-live-collector.service --since "5 minutes ago" --no-pager \
  | grep -E "RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_V1|VERDICT=RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_OK"

echo "TEST_RS_BOTTOM_RUNTIME_LIVE_COLLECTOR_TIMER_V1_OK"
