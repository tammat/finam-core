#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

REPO="src/finam_core/execution/protective_order_link_repository.py"
SCRIPT="src/scripts/place_protective_for_filled_entries.py"

grep -q "def mark_manual_protection_required" "$REPO"
grep -q "manual_protection_required" "$REPO"
grep -q "protective_stop_rejected_reason" "$REPO"
grep -q "PROTECTIVE_MANUAL_REQUIRED_MARK_FAILED" "$REPO"

grep -q "BROKER_UNCOVERED_POSITION_WARNING" "$SCRIPT"
grep -q "PROTECTIVE_MANUAL_PROTECTION_REQUIRED" "$SCRIPT"
grep -q "mark_manual_protection_required" "$SCRIPT"

python -m py_compile "$REPO"
python -m py_compile "$SCRIPT"

echo "PROTECTIVE_MANUAL_REQUIRED_FALLBACK_TEST_OK"
