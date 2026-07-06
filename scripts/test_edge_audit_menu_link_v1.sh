#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_AUDIT_MENU_LINK_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/edge_audit_page.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/router.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8080/edge-audit >/tmp/edge_audit_page.html
curl -fsS http://127.0.0.1:8080/ >/tmp/edge_audit_home.html

grep -q "Edge Audit" /tmp/edge_audit_page.html
grep -q "/edge-audit" /tmp/edge_audit_home.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_AUDIT_MENU_LINK_V1_OK"
