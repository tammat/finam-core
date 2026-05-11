#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f deploy/systemd/finam-order-ack-reconcile.service
test -f deploy/systemd/finam-order-ack-reconcile.timer

grep -q "Description=Finam Core Order ACK Reconciliation" deploy/systemd/finam-order-ack-reconcile.service
grep -q "Type=oneshot" deploy/systemd/finam-order-ack-reconcile.service
grep -q "User=finam" deploy/systemd/finam-order-ack-reconcile.service
grep -q "EnvironmentFile=/opt/finam-core/deploy/env/.env" deploy/systemd/finam-order-ack-reconcile.service
grep -q "src/scripts/reconcile_order_acks.py" deploy/systemd/finam-order-ack-reconcile.service

grep -q "OnUnitActiveSec=1min" deploy/systemd/finam-order-ack-reconcile.timer
grep -q "WantedBy=timers.target" deploy/systemd/finam-order-ack-reconcile.timer

python -m py_compile src/scripts/reconcile_order_acks.py

echo "SYSTEMD_ORDER_ACK_RECONCILE_TIMER_TEST_OK"
