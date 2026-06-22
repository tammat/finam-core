#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_REMOVE_PRE_JOURNALS_V1 ==="

pages=(
"/mobile"
"/summary"
"/edge"
"/compression-history"
)

for route in "${pages[@]}"; do

 html="$(curl -fsS "http://127.0.0.1:8088${route}")"

 if echo "$html" | grep -q "<pre>"; then
   echo "PRE_FOUND route=${route}"
   exit 1
 fi

 echo "PAGE_OK route=${route}"

done

echo "VERDICT=DASHBOARD_REMOVE_PRE_JOURNALS_OK"
echo "TEST_DASHBOARD_REMOVE_PRE_JOURNALS_V1_OK"
