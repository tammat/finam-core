#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f deploy/systemd/finam-order-ack-reconcile.service

grep -q "Type=oneshot" deploy/systemd/finam-order-ack-reconcile.service
grep -q "TimeoutStartSec=30" deploy/systemd/finam-order-ack-reconcile.service
grep -q "ExecStart=/opt/finam-core/venv/bin/python -u src/scripts/reconcile_order_acks.py" deploy/systemd/finam-order-ack-reconcile.service

echo "SYSTEMD_ORDER_ACK_RECONCILE_TIMEOUT_TEST_OK"
