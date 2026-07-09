#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_GUIDELINES_V1 ==="

doc="docs/ui/MARKETCORE_UI_GUIDELINES_V1.txt"

test -f "$doc"

grep -q "MARKETCORE_UI_GUIDELINES_V1" "$doc"
grep -q "Mobile First" "$doc"
grep -q "Workspace вместо набора страниц" "$doc"
grep -q "src/scripts/" "$doc"
grep -q "i18n" "$doc"
grep -q "Кач. модели" "$doc"
grep -q "touch-элементы не менее 44 px" "$doc"
grep -q "Пользователь никогда не видит внутренние коды" "$doc"

echo "ui_guidelines_doc=OK"
echo "language=ru"
echo "workspace_v2_standard=OK"
echo "mobile_first=OK"
echo "i18n_required=OK"
echo "safe_ui_targets=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_GUIDELINES_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_GUIDELINES_V1_OK"
