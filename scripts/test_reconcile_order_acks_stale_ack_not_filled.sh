#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RECONCILE_ORDER_ACKS_STALE_ACK_NOT_FILLED_START"

python -m py_compile src/scripts/reconcile_order_acks.py

python src/scripts/reconcile_order_acks.py | tee /tmp/reconcile_order_acks_stale_ack.out

grep -q "ORDER_ACK_RECONCILIATION" /tmp/reconcile_order_acks_stale_ack.out

if grep -q "ORDER_ACK_RECON_ISSUE" /tmp/reconcile_order_acks_stale_ack.out; then
  echo "TEST_RECONCILE_ORDER_ACKS_STALE_ACK_NOT_FILLED_HAS_CRITICAL_ISSUES"
  exit 1
fi

grep -q "ORDER_ACK_RECON_WARNING type=STALE_ACK_NOT_FILLED" /tmp/reconcile_order_acks_stale_ack.out

echo "TEST_RECONCILE_ORDER_ACKS_STALE_ACK_NOT_FILLED_OK"
