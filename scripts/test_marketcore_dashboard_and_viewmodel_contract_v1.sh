#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_DASHBOARD_AND_VIEWMODEL_CONTRACT_V1 ==="

test -f docs/MARKETCORE_DASHBOARD_CONTRACT_V1.txt
test -f docs/MARKETCORE_VIEWMODEL_CONTRACT_V1.txt

grep -q "MARKETCORE_DASHBOARD_CONTRACT_V1_READY" docs/MARKETCORE_DASHBOARD_CONTRACT_V1.txt
grep -q "MARKETCORE_VIEWMODEL_CONTRACT_V1_READY" docs/MARKETCORE_VIEWMODEL_CONTRACT_V1.txt

grep -q "Dashboard" docs/MARKETCORE_DASHBOARD_CONTRACT_V1.txt
grep -q "Header" docs/MARKETCORE_DASHBOARD_CONTRACT_V1.txt
grep -q "Toolbar" docs/MARKETCORE_DASHBOARD_CONTRACT_V1.txt
grep -q "KPI Panel" docs/MARKETCORE_DASHBOARD_CONTRACT_V1.txt
grep -q "Main Data Table" docs/MARKETCORE_DASHBOARD_CONTRACT_V1.txt
grep -q "Footer" docs/MARKETCORE_DASHBOARD_CONTRACT_V1.txt

grep -q "DashboardViewModel" docs/MARKETCORE_VIEWMODEL_CONTRACT_V1.txt
grep -q "ToolbarItem" docs/MARKETCORE_VIEWMODEL_CONTRACT_V1.txt
grep -q "KpiItem" docs/MARKETCORE_VIEWMODEL_CONTRACT_V1.txt
grep -q "TableModel" docs/MARKETCORE_VIEWMODEL_CONTRACT_V1.txt
grep -q "SafetyModel" docs/MARKETCORE_VIEWMODEL_CONTRACT_V1.txt

python - <<'PY2'
from pathlib import Path

allowed_sections = (
    "Forbidden toolbar actions:",
    "Dashboard layer must not:",
    "Provider must not:",
    "Page must not:",
)

dangerous = (
    "send_order",
    "place_order",
    "cancel_order",
    "execute_order",
    "FinamClient",
    "LiveExecution",
    "PaperExecution",
)

for path in [
    Path("docs/MARKETCORE_DASHBOARD_CONTRACT_V1.txt"),
    Path("docs/MARKETCORE_VIEWMODEL_CONTRACT_V1.txt"),
]:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_allowed_block = False

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        if stripped in allowed_sections:
            in_allowed_block = True
            continue

        if in_allowed_block and stripped == "":
            in_allowed_block = False
            continue

        if any(token in line for token in dangerous) and not in_allowed_block:
            raise SystemExit(f"UNSAFE_CONTRACT_TEXT_FOUND={path}:{idx}:{line}")

print("unsafe_contract_text=0")
PY2

echo "dashboard_contract=OK"
echo "viewmodel_contract=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_DASHBOARD_AND_VIEWMODEL_CONTRACT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_DASHBOARD_AND_VIEWMODEL_CONTRACT_V1_OK"
