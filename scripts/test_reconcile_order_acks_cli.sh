#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

OUT="/tmp/reconcile_order_acks_cli.out"

ORDER_ACK_RECONCILE_LIMIT=100 \
PYTHONPATH=src \
/opt/finam-core/venv/bin/python -u src/scripts/reconcile_order_acks.py > "$OUT" 2>&1 || RC=$?

RC="${RC:-0}"

grep -q "ORDER_ACK_RECONCILIATION" "$OUT"
grep -q "acks=" "$OUT"
grep -q "broker_orders=" "$OUT"
grep -q "issues=" "$OUT"

# Русский комментарий: если есть реальные issues, CLI может вернуть 1; это не ошибка запуска.
if [ "$RC" != "0" ] && [ "$RC" != "1" ]; then
  cat "$OUT"
  echo "Unexpected exit code: $RC"
  exit "$RC"
fi

cat "$OUT"

echo "RECONCILE_ORDER_ACKS_CLI_TEST_OK"
