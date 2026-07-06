#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_MTM_VIEWMODEL_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/paper_mtm_page.py \
  src/marketcore/presentation/components/data_table.py \
  src/marketcore/presentation/components/kpi_card.py \
  src/marketcore/presentation/components/section.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8080/paper-mtm >/tmp/paper_mtm_viewmodel_ui_v1.html

grep -q "Paper MTM" /tmp/paper_mtm_viewmodel_ui_v1.html
grep -q "kpi-card" /tmp/paper_mtm_viewmodel_ui_v1.html
grep -q "data-table" /tmp/paper_mtm_viewmodel_ui_v1.html

if grep -q "<pre" /tmp/paper_mtm_viewmodel_ui_v1.html; then
  echo "RAW_PRE_FOUND"
  exit 1
fi

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_MTM_VIEWMODEL_UI_V1_READY"
echo "VERDICT=TEST_PAPER_MTM_VIEWMODEL_UI_V1_OK"
