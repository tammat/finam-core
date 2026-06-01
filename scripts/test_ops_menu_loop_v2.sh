#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "TEST_OPS_MENU_LOOP_V2_START"

bash -n scripts/ops/finam_ops.sh

grep -q "0) выход" scripts/ops/finam_ops.sh
grep -q "ДЕЙСТВИЕ: DASHBOARD" scripts/ops/finam_ops.sh
grep -q "Нажмите Enter для возврата в меню" scripts/ops/finam_ops.sh
grep -q 'read -r -p "Выберите действие: "' scripts/ops/finam_ops.sh

echo "TEST_OPS_MENU_LOOP_V2_OK"
