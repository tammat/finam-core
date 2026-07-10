#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_RUNTIME_PLATFORM_DRIVER_INVENTORY_V1 ==="

inventory_script=\
"src/scripts/presentation/runtime_platform_driver_inventory_v1.py"

report=\
"reports/marketcore_runtime_platform_driver_inventory_v1.txt"

test -f "$inventory_script" || {
  echo "FILE_NOT_FOUND=$inventory_script"
  exit 1
}

PYTHONPYCACHEPREFIX=/tmp/marketcore_platform_driver_inventory_v1 \
PYTHONPATH=src \
python -m py_compile "$inventory_script"

PYTHONPATH=src \
python "$inventory_script" | tee "$report"

required_sections=(
  "PLATFORM_DRIVER_PROTOCOL"
  "PYTHON_DRIVER_CLASS_CANDIDATES"
  "COMPLETE_PYTHON_PLATFORM_DRIVERS"
  "EXPLICIT_PLATFORM_DRIVER_IMPLEMENTATIONS"
  "PLATFORM_DRIVER_IMPORTS"
  "JAVASCRIPT_DRIVER_CANDIDATES"
  "ANALYSIS_INPUTS"
  "DECISION"
)

for section in "${required_sections[@]}"; do
  grep -q "$section" "$report" || {
    echo "REPORT_SECTION_NOT_FOUND=$section"
    exit 1
  }
done

grep -Eq \
  '^platform_driver_found=[01]$' \
  "$report"

grep -q \
  '^inventory_only=1$' \
  "$report"

grep -q \
  '^platform_driver_created=0$' \
  "$report"

grep -q \
  '^runtime_core_changed=0$' \
  "$report"

grep -q \
  '^architecture_changed=0$' \
  "$report"

grep -q \
  '^VERDICT=MARKETCORE_RUNTIME_PLATFORM_DRIVER_INVENTORY_V1_READY$' \
  "$report"

echo "inventory_report=$report"
echo "platform_driver_inventory=OK"
echo "platform_driver_created=0"
echo "runtime_core_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
"VERDICT=TEST_MARKETCORE_RUNTIME_PLATFORM_DRIVER_INVENTORY_V1_OK"
