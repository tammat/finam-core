#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
SCRIPT="src/scripts/research/build_net_first_enforcement_post_apply_observability_v1.py"

echo "=== TEST NET FIRST POST APPLY OBSERVABILITY SEMANTICS V2 ==="

PYTHONPATH=src "$PY" -m py_compile "$SCRIPT"

OUTPUT="$(
    PYTHONPATH=src "$PY" "$SCRIPT"
)"

printf '%s\n' "$OUTPUT"

grep -q '^candidates_evaluated=30$' <<< "$OUTPUT"
grep -q '^net_first_reject=30$' <<< "$OUTPUT"

grep -q \
  '^reject_without_oos_admission_observed=26$' \
  <<< "$OUTPUT"

grep -q \
  '^counterfactual_downstream_saved_finalized=0$' \
  <<< "$OUTPUT"

grep -q \
  '^actual_downstream_saved_claimed=0$' \
  <<< "$OUTPUT"

if grep -q '^actual_downstream_saved=' <<< "$OUTPUT"; then
    echo "ERROR=UNVALIDATED_DOWNSTREAM_SAVINGS_CLAIM"
    exit 1
fi

grep -q '^db_writes_performed=0$' <<< "$OUTPUT"
grep -q '^enforcement_applied=1$' <<< "$OUTPUT"
grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

echo "observed_no_admission_not_equal_savings=1"
echo "counterfactual_required=1"
echo "VERDICT=TEST_NET_FIRST_POST_APPLY_OBSERVABILITY_SEMANTICS_V2_OK"
