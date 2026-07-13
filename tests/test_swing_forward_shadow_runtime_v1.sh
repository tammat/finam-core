#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd -- "$SCRIPT_DIR/.." && pwd)}"
cd "$PROJECT_ROOT"

PYTHON="${PYTHON:-$PROJECT_ROOT/.venv/bin/python}"
GUARD="${SWING_SHADOW_GUARD:-$PROJECT_ROOT/src/scripts/build_swing_shadow_experiment_guard_v1.py}"
ROUTER="${SWING_SHADOW_ROUTER:-$PROJECT_ROOT/src/scripts/run_swing_forward_shadow_router_v1.py}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

GUARD_LOG="$TMP_DIR/guard.log"
ROUTER_LOG="$TMP_DIR/router.log"

echo "=== TEST_SWING_FORWARD_SHADOW_RUNTIME_V1 ==="

test -x "$PYTHON" || {
    echo "ERROR=PYTHON_NOT_EXECUTABLE path=$PYTHON"
    echo "VERDICT=TEST_SWING_FORWARD_SHADOW_RUNTIME_V1_FAILED"
    exit 1
}

test -f "$GUARD" || {
    echo "ERROR=MISSING_FILE path=$GUARD"
    echo "VERDICT=TEST_SWING_FORWARD_SHADOW_RUNTIME_V1_FAILED"
    exit 1
}

test -f "$ROUTER" || {
    echo "ERROR=MISSING_FILE path=$ROUTER"
    echo "VERDICT=TEST_SWING_FORWARD_SHADOW_RUNTIME_V1_FAILED"
    exit 1
}

echo
echo "=== GUARD ==="

if ! env PYTHONDONTWRITEBYTECODE=1 \
    "$PYTHON" "$GUARD" 2>&1 | tee "$GUARD_LOG"
then
    echo "ERROR=SWING_SHADOW_GUARD_FAILED"
    echo "VERDICT=TEST_SWING_FORWARD_SHADOW_RUNTIME_V1_FAILED"
    exit 1
fi

echo
echo "=== ROUTER ==="

if ! env PYTHONDONTWRITEBYTECODE=1 \
    "$PYTHON" "$ROUTER" 2>&1 | tee "$ROUTER_LOG"
then
    echo "ERROR=SWING_FORWARD_SHADOW_ROUTER_FAILED"
    echo "VERDICT=TEST_SWING_FORWARD_SHADOW_RUNTIME_V1_FAILED"
    exit 1
fi

echo
echo "=== SAFETY ASSERTIONS ==="

grep -q '^unsafe=0$' "$ROUTER_LOG" || {
    echo "ERROR=UNSAFE_STATE_DETECTED"
    grep '^unsafe=' "$ROUTER_LOG" || true
    echo "VERDICT=TEST_SWING_FORWARD_SHADOW_RUNTIME_V1_FAILED"
    exit 1
}

grep -q '^broker_orders=0$' "$ROUTER_LOG" || {
    echo "ERROR=BROKER_ORDER_GUARD_FAILED"
    grep '^broker_orders=' "$ROUTER_LOG" || true
    echo "VERDICT=TEST_SWING_FORWARD_SHADOW_RUNTIME_V1_FAILED"
    exit 1
}

grep -q '^final_oos_opened=0$' "$ROUTER_LOG" || {
    echo "ERROR=FINAL_OOS_OPENED"
    grep '^final_oos_opened=' "$ROUTER_LOG" || true
    echo "VERDICT=TEST_SWING_FORWARD_SHADOW_RUNTIME_V1_FAILED"
    exit 1
}

grep -q '^VERDICT=SWING_FORWARD_SHADOW_ROUTER_V1_OK$' "$ROUTER_LOG" || {
    echo "ERROR=ROUTER_SUCCESS_VERDICT_MISSING"
    echo "VERDICT=TEST_SWING_FORWARD_SHADOW_RUNTIME_V1_FAILED"
    exit 1
}

echo "unsafe=0"
echo "broker_orders=0"
echo "final_oos_opened=0"
echo "VERDICT=TEST_SWING_FORWARD_SHADOW_RUNTIME_V1_OK"
