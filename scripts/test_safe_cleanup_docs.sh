#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f scripts/clear_test_projections_safe.sh
test -x scripts/clear_test_projections_safe.sh

grep -q "CONFIRM_CLEAR_TEST_PROJECTIONS" scripts/clear_test_projections_safe.sh
grep -q "position_projection" scripts/clear_test_projections_safe.sh
grep -q "order_projection" scripts/clear_test_projections_safe.sh
grep -q "event_dead_letters" scripts/clear_test_projections_safe.sh
grep -q "CLEARED_TEST_PROJECTIONS_OK" scripts/clear_test_projections_safe.sh

echo "SAFE_CLEANUP_SCRIPT_TEST_OK"
