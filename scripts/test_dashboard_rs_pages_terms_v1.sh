#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_RS_PAGES_TERMS_V1 ==="

pages=(
"/rs-bottom-forward"
"/rs-breakout-confirmation"
"/brent-rollover-edge"
)

for route in "${pages[@]}"; do

 html="$(curl -fsS "http://127.0.0.1:8088${route}")"

 if echo "$html" | grep -qi \
   "RS Bottom Forward|RS Breakout Confirmation|Brent Rollover|PF Forward|PF Historical|Avg Return"; then
   echo "ENGLISH_RS_TERM_FOUND route=${route}"
   exit 1
 fi

 echo "PAGE_OK route=${route}"

done

echo "VERDICT=DASHBOARD_RS_PAGES_TERMS_OK"
echo "TEST_DASHBOARD_RS_PAGES_TERMS_V1_OK"
