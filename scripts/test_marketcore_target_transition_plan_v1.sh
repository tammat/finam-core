#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

plan="docs/vision/MARKETCORE_TARGET_TRANSITION_PLAN_V1.md"

test -s "$plan" || {
  echo "PLAN_NOT_FOUND=$plan"
  exit 1
}

required_terms=(
  "Status: LOCKED"
  "Stage 0 - Lock The Baseline"
  "Stage 1 - Presentation Inventory"
  "Stage 2 - Domain RenderTree Contract"
  "Stage 3 - Runtime And Platform Driver Boundary"
  "Stage 4 - Canonical Navigation Containers"
  "Stage 5 - Policy-Governed Actions"
  "Stage 6 - Complete I18n"
  "Stage 7 - Live Profit Funnel Data"
  "Stage 8 - Operator Workspace"
  "Stage 9 - Retire Legacy Presentation"
  "Critical Exception Protocol"
  "Commit, tag, push, migration, service restart and destructive SQL require explicit operator approval."
  "VERDICT=MARKETCORE_TARGET_TRANSITION_PLAN_V1_LOCKED"
)

for term in "${required_terms[@]}"; do
  grep -Fq "$term" "$plan" || {
    echo "PLAN_TERM_NOT_FOUND=$term"
    exit 1
  }
done

for stage in {0..9}; do
  count="$(grep -c "^## [0-9][0-9]*\. Stage $stage -" "$plan")"
  test "$count" -eq 1 || {
    echo "INVALID_STAGE_COUNT=$stage:$count"
    exit 1
  }
done

grep -Fq "HTML, CSS and DOM semantics are absent from the domain RenderTree" "$plan"
grep -Fq "Unverified data must never produce a green operational recommendation." "$plan"

echo "plan_status=LOCKED"
echo "ordered_stages=10"
echo "critical_exception_protocol=OK"
echo "restricted_git_operations=OPERATOR_APPROVAL_REQUIRED"
echo "VERDICT=TEST_MARKETCORE_TARGET_TRANSITION_PLAN_V1_OK"
