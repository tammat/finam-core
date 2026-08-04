#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
FILE="$ROOT/src/scripts/build_marketcore_ui_8080_route_health_matrix_v1.py"
LOG="/tmp/marketcore_ui_route_health_matrix_runtime_v2_v1.log"

cd "$ROOT" || exit 1

echo \
  "=== TEST_MARKETCORE_UI_ROUTE_HEALTH_MATRIX_RUNTIME_V2_V1 ==="

[[ -s "$FILE" ]] || {
    echo "ERROR=builder_missing"
    exit 1
}

PYTHONPATH=src \
/opt/finam-core/venv/bin/python -m py_compile \
  "$FILE"

curl -fsS \
  "http://127.0.0.1:8080/" \
  >/tmp/marketcore_ui_runtime_v2_shell.html

grep -q \
  'data-marketcore-ui-runtime="v2"' \
  /tmp/marketcore_ui_runtime_v2_shell.html

PYTHONPATH=src \
DATABASE_URL="${DATABASE_URL:-postgresql:///finam_core}" \
/opt/finam-core/venv/bin/python "$FILE" |
  tee "$LOG"

required=(
    "domains_total=9"
    "healthy_domains=9"
    "unhealthy_domains=0"
    "mapping_contract=EXPLICIT_AGGREGATED_DOMAINS_V1"
    "runtime_contract=DOMAIN_RENDER_TREE_V2"
    "legacy_html_routes_required=0"
    "VERDICT=MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_RUNTIME_V2_V1_READY"
)

for token in "${required[@]}"
do
    grep -qF "$token" "$LOG" || {
        echo "ERROR=required_output_missing:$token"
        exit 1
    }
done

ROUTES_TOTAL="$(
    awk -F= '/^routes_total=/{print $2; exit}' "$LOG"
)"

ROWS_WRITTEN="$(
    awk -F= '/^rows_written=/{print $2; exit}' "$LOG"
)"

HEALTHY_ROUTES="$(
    awk -F= '/^healthy_routes=/{print $2; exit}' "$LOG"
)"

UNHEALTHY_ROUTES="$(
    awk -F= '/^unhealthy_routes=/{print $2; exit}' "$LOG"
)"

[[ "$ROUTES_TOTAL" =~ ^[0-9]+$ ]] || {
    echo "ERROR=invalid_routes_total:$ROUTES_TOTAL"
    exit 1
}

[[ "$ROWS_WRITTEN" == "$ROUTES_TOTAL" ]] || {
    echo \
      "ERROR=rows_written_mismatch:${ROWS_WRITTEN}:${ROUTES_TOTAL}"
    exit 1
}

[[ "$HEALTHY_ROUTES" == "$ROUTES_TOTAL" ]] || {
    echo \
      "ERROR=healthy_routes_mismatch:${HEALTHY_ROUTES}:${ROUTES_TOTAL}"
    exit 1
}

[[ "$UNHEALTHY_ROUTES" == "0" ]] || {
    echo "ERROR=unhealthy_routes:$UNHEALTHY_ROUTES"
    grep '^ROUTE ' "$LOG" | grep 'http_ok=0' || true
    exit 1
}

DB_STATE="$(
    psql -X -d finam_core -AtF '|' -c "
    SELECT
        count(*),
        count(*) FILTER (WHERE http_ok),
        count(*) FILTER (WHERE NOT http_ok),
        count(*) FILTER (
            WHERE source_version =
                'MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_RUNTIME_V2_V1'
        )
    FROM
        marketcore_ui.
        marketcore_ui_route_health_matrix_v1;
    "
)"

echo "db_state=$DB_STATE"

EXPECTED_STATE="${ROUTES_TOTAL}|${ROUTES_TOTAL}|0|${ROUTES_TOTAL}"

[[ "$DB_STATE" == "$EXPECTED_STATE" ]] || {
    echo "ERROR=db_state_invalid:$DB_STATE"
    echo "expected_state=$EXPECTED_STATE"
    exit 1
}

echo "routes_total=$ROUTES_TOTAL"
echo "rows_written=$ROWS_WRITTEN"
echo "healthy_routes=$HEALTHY_ROUTES"
echo "unhealthy_routes=0"
echo "healthy_domains=9"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
  "VERDICT=TEST_MARKETCORE_UI_ROUTE_HEALTH_MATRIX_RUNTIME_V2_V1_OK"
