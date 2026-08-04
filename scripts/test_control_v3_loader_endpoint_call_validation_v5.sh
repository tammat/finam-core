#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
TARGET="$ROOT/scripts/repair_control_v3_historical_corrections_loader_v2.sh"

echo "=== TEST CONTROL V3 LOADER ENDPOINT CALL VALIDATION V5 ==="

[[ -f "$TARGET" ]] || {
    echo "ERROR=target_missing:$TARGET"
    exit 1
}

bash -n "$TARGET"

legacy_marker_count="$(
    grep -c 'resolver_loader_endpoint_count:' "$TARGET" || true
)"

new_marker_count="$(
    grep -c 'resolver_loader_endpoint_call_count:' "$TARGET" || true
)"

ast_walk_count="$(
    grep -c 'ast\.walk(loader_method)' "$TARGET" || true
)"

get_json_validation_count="$(
    grep -c 'function_name != "get_json"' "$TARGET" || true
)"

endpoint_match_count="$(
    grep -c 'ENDPOINT in endpoint_values' "$TARGET" || true
)"

echo "legacy_validation_marker_count=$legacy_marker_count"
echo "endpoint_call_validation_marker_count=$new_marker_count"
echo "loader_ast_walk_count=$ast_walk_count"
echo "get_json_call_filter_count=$get_json_validation_count"
echo "endpoint_argument_match_count=$endpoint_match_count"

[[ "$legacy_marker_count" -eq 0 ]] || {
    echo "ERROR=legacy_endpoint_validation_present"
    exit 1
}

[[ "$new_marker_count" -eq 1 ]] || {
    echo "ERROR=endpoint_call_validation_marker_count:$new_marker_count"
    exit 1
}

[[ "$ast_walk_count" -eq 1 ]] || {
    echo "ERROR=loader_ast_walk_count:$ast_walk_count"
    exit 1
}

[[ "$get_json_validation_count" -eq 1 ]] || {
    echo "ERROR=get_json_call_filter_count:$get_json_validation_count"
    exit 1
}

[[ "$endpoint_match_count" -eq 1 ]] || {
    echo "ERROR=endpoint_argument_match_count:$endpoint_match_count"
    exit 1
}

echo "source_contract=OK"
echo "writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_CONTROL_V3_LOADER_ENDPOINT_CALL_VALIDATION_V5_OK"
