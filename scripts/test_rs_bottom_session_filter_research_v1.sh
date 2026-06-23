#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BOTTOM_SESSION_FILTER_RESEARCH_V1 ==="

out="$(python3 src/scripts/research/build_rs_bottom_session_filter_research_v1.py)"

echo "$out"

echo "$out" | grep -q "RS_BOTTOM_SESSION_FILTER_RESEARCH_SUMMARY"
echo "$out" | grep -Eq "VERDICT=RS_BOTTOM_SESSION_FILTER_(HAS_CANDIDATES|NO_POSITIVE_EDGE)"
echo "$out" | grep -q "db_update=0"
echo "$out" | grep -q "runtime_changed=0"
echo "$out" | grep -q "execution_changed=0"

echo "TEST_RS_BOTTOM_SESSION_FILTER_RESEARCH_V1_OK"
