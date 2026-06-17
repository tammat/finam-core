#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST OPERATIONAL DASHBOARD CLEANUP V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"

stale_files=(
  "src/scripts/research/wire_operational_dashboard_v1_1.py"
  "src/scripts/research/wire_operational_dashboard_v1_2.py"
  "src/scripts/research/wire_operational_dashboard_v1_3.py"
  "scripts/test_operational_dashboard_wiring_v1_1.sh"
  "scripts/test_operational_dashboard_wiring_v1_2.sh"
  "scripts/test_operational_dashboard_wiring_v1_3.sh"
)

for f in "${stale_files[@]}"; do
  if [ -e "$f" ]; then
    echo "FAIL_STALE_ARTIFACT_PRESENT $f"
    exit 1
  fi
done

required_files=(
  "src/ui/readonly_runtime_dashboard_v1.py"
  "src/ui/templates/v3_dashboard.html"
  "src/scripts/research/wire_operational_dashboard_v1_4.py"
  "scripts/test_operational_dashboard_wiring_v1_4.sh"
  "scripts/test_operational_dashboard_wiring_v1_4_fix.sh"
  "src/scripts/research/polish_operational_dashboard_ru_status_v1.py"
  "scripts/test_operational_dashboard_ru_status_polish_v1.sh"
  "src/scripts/research/add_operational_dashboard_metrics_summary_v1.py"
  "scripts/test_operational_dashboard_metrics_summary_v1.sh"
)

for f in "${required_files[@]}"; do
  test -f "$f" || { echo "FAIL_REQUIRED_FILE_MISSING $f"; exit 1; }
done

python3 -m py_compile \
  src/ui/readonly_runtime_dashboard_v1.py \
  src/scripts/research/wire_operational_dashboard_v1_4.py \
  src/scripts/research/polish_operational_dashboard_ru_status_v1.py \
  src/scripts/research/add_operational_dashboard_metrics_summary_v1.py

grep -q "OPERATIONAL_DASHBOARD_WIRING_V1" src/ui/templates/v3_dashboard.html
grep -q "OPERATIONAL_DASHBOARD_METRICS_SUMMARY_V1" src/ui/templates/v3_dashboard.html
grep -q "Текущих paper-позиций" src/ui/templates/v3_dashboard.html
grep -q "Карантин" src/ui/templates/v3_dashboard.html

curl -fss http://127.0.0.1:8088/ \
  | grep -q "Текущий net qty"

curl -fss http://127.0.0.1:8088/v3 \
  | grep -q "Clean V3 flat"

echo "VERDICT=OPERATIONAL_DASHBOARD_CLEANUP_OK"
echo "TEST_OPERATIONAL_DASHBOARD_CLEANUP_V1_OK"
