#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== DASHBOARD_NAVIGATION_AUDIT_V1 ==="

BASE="http://127.0.0.1:8088"

routes=(
  "/"
  "/rs-bottom-runtime-dry-run"
  "/active-futures-universe"
  "/equities"
  "/leaderboard"
  "/edge-stability"
  "/rs-bottom-forward"
  "/rs-bottom-clean"
  "/rs-bottom-paper"
)

ok=0
fail=0

for route in "${routes[@]}"; do

  echo
  echo "CHECK_ROUTE ${route}"

  file="/tmp/dashboard_audit_$(echo "$route" | tr '/' '_').html"

  if curl -fsS "${BASE}${route}" > "$file"; then

      if grep -q "Меню 8088" "$file"; then
          menu_ok=1
      else
          menu_ok=0
      fi

      if grep -q 'href="/"' "$file"; then
          home_ok=1
      else
          home_ok=0
      fi

      echo "PAGE_OK route=${route} menu=${menu_ok} home=${home_ok}"

      if [ "$menu_ok" -eq 1 ] && [ "$home_ok" -eq 1 ]; then
          ok=$((ok+1))
      else
          fail=$((fail+1))
      fi

  else
      echo "PAGE_FAIL route=${route}"
      fail=$((fail+1))
  fi

done

echo
echo "AUDIT_SUMMARY"
echo "ok=${ok}"
echo "fail=${fail}"

if [ "$fail" -eq 0 ]; then
    echo "VERDICT=DASHBOARD_NAVIGATION_AUDIT_OK"
else
    echo "VERDICT=DASHBOARD_NAVIGATION_AUDIT_FAILED"
    exit 1
fi

echo "TEST_DASHBOARD_NAVIGATION_AUDIT_V1_OK"
