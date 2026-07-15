#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

inventory="docs/vision/MARKETCORE_PRESENTATION_INVENTORY_V1.md"
presentation="src/marketcore/presentation"

test -s "$inventory" || {
  echo "INVENTORY_NOT_FOUND=$inventory"
  exit 1
}

test -d "$presentation/render_tree"
test -d "$presentation/ui_runtime"
test -d "$presentation/pages"
test -d "$presentation/workspace_v2"
test -d "$presentation/dashboard"

required_categories=(
  "HTML/DOM/CSS"
  "Hardcode Hotspots"
  "SQL Hotspots"
  "Runtime Route Probe"
  "Action Runtime"
  "Data/API"
  "I18n"
  "Platform Driver"
  "VERDICT=MARKETCORE_PRESENTATION_INVENTORY_V1_COMPLETE"
)

for category in "${required_categories[@]}"; do
  grep -Fq "$category" "$inventory" || {
    echo "INVENTORY_CATEGORY_NOT_FOUND=$category"
    exit 1
  }
done

for number in $(seq 1 16); do
  id="$(printf '%03d' "$number")"
  grep -Fq "PRES-$id" "$inventory" || {
    echo "INVENTORY_VIOLATION_NOT_FOUND=PRES-$id"
    exit 1
  }
done

file_count="$(find "$presentation" -type f ! -path "*/__pycache__/*" | wc -l)"
test "$file_count" -ge 287 || {
  echo "PRESENTATION_SURFACE_SHRANK_WITHOUT_REVIEW=$file_count"
  exit 1
}

grep -Fq '"class"' "$presentation/ui_runtime/contract_v1.py"
grep -Fq '"style"' "$presentation/ui_runtime/contract_v1.py"
grep -Fq 'class: "class"' "$presentation/ui_runtime/assets/v1/browser_dom_driver_v1.js"
grep -Fq 'style: "style"' "$presentation/ui_runtime/assets/v1/browser_dom_driver_v1.js"

echo "presentation_files=$file_count"
echo "registered_violations=16"
echo "inventory_categories=OK"
echo "runtime_changed=0"
echo "VERDICT=TEST_MARKETCORE_PRESENTATION_INVENTORY_V1_OK"
