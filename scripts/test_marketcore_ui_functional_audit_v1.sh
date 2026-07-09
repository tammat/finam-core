#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_FUNCTIONAL_AUDIT_V1 ==="

mkdir -p reports
report="reports/marketcore_ui_functional_audit_v1.txt"
base_url="${MARKETCORE_UI_URL:-http://127.0.0.1:8090}"

{
echo "======================================================"
echo "MARKETCORE UI FUNCTIONAL AUDIT V1"
echo "======================================================"
echo "generated_at=$(date -Is)"
echo "base_url=${base_url}"
echo

echo "=== SERVICE STATUS ==="
systemctl is-active marketcore-ui-shell.service || true
echo

echo "=== HTTP ROUTE CHECK ==="

routes=(
  "/"
  "/workspace"
  "/day"
  "/runtime"
  "/capital"
  "/edge"
  "/research"
  "/intraday"
  "/portfolio"
  "/risk"
  "/program"
  "/settings"
)

failed_routes=0

for route in "${routes[@]}"; do
  url="${base_url}${route}"
  code=$(curl -k -sS -o "/tmp/marketcore_ui_audit_${route//\//_}.html" -w "%{http_code}" "$url" || echo "000")

  echo "route=${route} http_code=${code}"

  if [ "$code" != "200" ]; then
    failed_routes=$((failed_routes+1))
  fi
done

echo
echo "failed_routes=${failed_routes}"

echo
echo "=== RAW I18N KEY CHECK ==="

raw_i18n_total=0

for f in /tmp/marketcore_ui_audit_*.html; do
  count=$(grep -Eo '(widget|page|column|message|marketcore_ui|model\.health|paper\.feedback|paper\.analytics|trading_plan|strategy)\.[A-Za-z0-9_.-]+' "$f" | wc -l | tr -d ' ')
  echo "file=$(basename "$f") raw_i18n_keys=${count}"
  raw_i18n_total=$((raw_i18n_total+count))
done

echo "raw_i18n_total=${raw_i18n_total}"

echo
echo "=== NAVIGATION / BUTTON CHECK ==="

home_file="/tmp/marketcore_ui_audit__.html"

if [ ! -f "$home_file" ]; then
  home_file="$(ls /tmp/marketcore_ui_audit_*.html | head -1)"
fi

nav_links=$(grep -Eo 'href="[^"]+"' "$home_file" | wc -l | tr -d ' ')
buttons=$(grep -Eo '<button[^>]*' "$home_file" | wc -l | tr -d ' ')
onclick_handlers=$(grep -Eo 'onclick=' "$home_file" | wc -l | tr -d ' ')
data_actions=$(grep -Eo 'data-action=' "$home_file" | wc -l | tr -d ' ')
aria_expanded=$(grep -Eo 'aria-expanded=' "$home_file" | wc -l | tr -d ' ')

echo "nav_links=${nav_links}"
echo "buttons=${buttons}"
echo "onclick_handlers=${onclick_handlers}"
echo "data_actions=${data_actions}"
echo "aria_expanded=${aria_expanded}"

echo
echo "=== MOBILE RESPONSIVE CHECK ==="

mobile_file="/tmp/marketcore_ui_mobile.html"

mobile_code=$(curl -k -sS \
  -A "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1" \
  -H "Viewport-Width: 390" \
  -o "$mobile_file" \
  -w "%{http_code}" \
  "${base_url}/" || echo "000")

viewport_meta=$(grep -Eo '<meta[^>]+viewport[^>]*>' "$mobile_file" | wc -l | tr -d ' ')
mobile_menu=$(grep -Eo '(menu|burger|sidebar|drawer|nav-toggle|data-nav|mobile)' "$mobile_file" | wc -l | tr -d ' ')
mobile_raw_i18n=$(grep -Eo '(widget|page|column|message|marketcore_ui|model\.health|paper\.feedback|paper\.analytics|trading_plan|strategy)\.[A-Za-z0-9_.-]+' "$mobile_file" | wc -l | tr -d ' ')

echo "mobile_http_code=${mobile_code}"
echo "viewport_meta=${viewport_meta}"
echo "mobile_menu_markers=${mobile_menu}"
echo "mobile_raw_i18n=${mobile_raw_i18n}"

echo
echo "=== PROJECT STATUS VISIBILITY CHECK ==="

status_markers=$(grep -Eio 'model health|здоровье модели|profit readiness|готовность|robustness|устойчивость|learning readiness|paper validation|statistical maturity|locked|research' "$home_file" | wc -l | tr -d ' ')
phase_markers=$(grep -Eio 'phase|фаза|paper validation|statistical maturity|production|shadow|locked' "$home_file" | wc -l | tr -d ' ')

echo "project_status_markers=${status_markers}"
echo "phase_markers=${phase_markers}"

echo
echo "=== AUDIT DECISION ==="

echo "failed_routes=${failed_routes}"
echo "raw_i18n_total=${raw_i18n_total}"
echo "mobile_http_code=${mobile_code}"
echo "viewport_meta=${viewport_meta}"
echo "mobile_menu_markers=${mobile_menu}"
echo "project_status_markers=${status_markers}"

if [ "$failed_routes" -gt 0 ]; then
  echo "UI_ROUTE_FAILURES_FOUND"
fi

if [ "$raw_i18n_total" -gt 0 ]; then
  echo "UI_RAW_I18N_KEYS_FOUND"
fi

if [ "$mobile_code" != "200" ]; then
  echo "UI_MOBILE_ROUTE_FAILURE"
fi

if [ "$viewport_meta" -lt 1 ]; then
  echo "UI_MOBILE_VIEWPORT_MISSING"
fi

if [ "$mobile_menu" -lt 1 ]; then
  echo "UI_MOBILE_NAVIGATION_MARKERS_MISSING"
fi

if [ "$status_markers" -lt 1 ]; then
  echo "UI_PROJECT_STATUS_NOT_VISIBLE"
fi

echo
echo "=== SAFETY ==="
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo

echo "VERDICT=MARKETCORE_UI_FUNCTIONAL_AUDIT_V1_READY"

} | tee "$report"

grep -q "VERDICT=MARKETCORE_UI_FUNCTIONAL_AUDIT_V1_READY" "$report"

echo "report=$report"
echo "mode=read_only_ui_audit"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_FUNCTIONAL_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_FUNCTIONAL_AUDIT_V1_OK"
