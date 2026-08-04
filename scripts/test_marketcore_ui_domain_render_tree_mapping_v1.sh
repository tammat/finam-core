#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
FILE="$ROOT/src/scripts/audit_marketcore_ui_domain_render_tree_mapping_v1.py"
LOG="/tmp/marketcore_ui_domain_render_tree_mapping_v1.log"

cd "$ROOT" || exit 1

echo "=== TEST_MARKETCORE_UI_DOMAIN_RENDER_TREE_MAPPING_V1 ==="

[[ -s "$FILE" ]] || {
    echo "ERROR=mapping_audit_missing"
    exit 1
}

PYTHONPATH=src \
/opt/finam-core/venv/bin/python -m py_compile "$FILE"

PYTHONPATH=src \
/opt/finam-core/venv/bin/python "$FILE" |
  tee "$LOG"

grep -qF \
  "VERDICT=MARKETCORE_UI_DOMAIN_RENDER_TREE_MAPPING_V1_READY" \
  "$LOG"

ROUTES_TOTAL="$(
    awk -F= '/^routes_total=/{print $2; exit}' "$LOG"
)"

MAPPED_ROUTES="$(
    awk -F= '/^mapped_routes=/{print $2; exit}' "$LOG"
)"

HEALTHY_ROUTES="$(
    awk -F= '/^healthy_routes=/{print $2; exit}' "$LOG"
)"

UNHEALTHY_DOMAINS="$(
    awk -F= '/^unhealthy_domains=/{print $2; exit}' "$LOG"
)"

[[ "$ROUTES_TOTAL" =~ ^[0-9]+$ ]] || {
    echo "ERROR=invalid_routes_total:$ROUTES_TOTAL"
    exit 1
}

[[ "$MAPPED_ROUTES" == "$ROUTES_TOTAL" ]] || {
    echo "ERROR=unmapped_routes:${MAPPED_ROUTES}:${ROUTES_TOTAL}"
    exit 1
}

[[ "$HEALTHY_ROUTES" == "$ROUTES_TOTAL" ]] || {
    echo "ERROR=unhealthy_routes:${HEALTHY_ROUTES}:${ROUTES_TOTAL}"
    exit 1
}

[[ "$UNHEALTHY_DOMAINS" == "0" ]] || {
    echo "ERROR=unhealthy_domains:$UNHEALTHY_DOMAINS"
    grep '^DOMAIN ' "$LOG" | grep 'healthy=0' || true
    exit 1
}

echo "routes_total=$ROUTES_TOTAL"
echo "mapped_routes=$MAPPED_ROUTES"
echo "healthy_routes=$HEALTHY_ROUTES"
echo "unhealthy_domains=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
  "VERDICT=TEST_MARKETCORE_UI_DOMAIN_RENDER_TREE_MAPPING_V1_OK"
