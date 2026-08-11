#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
SCRIPT="src/scripts/research/build_net_first_enforcement_insertion_point_finalization_v1.py"

echo "=== TEST NET FIRST ENFORCEMENT INSERTION POINT FINALIZATION V1 ==="

PYTHONPATH=src "$PY" -m py_compile "$SCRIPT"

OUTPUT="$(
    PYTHONPATH=src "$PY" "$SCRIPT"
)"

printf '%s\n' "$OUTPUT"

grep -q '^candidate_source_identified=1$' <<< "$OUTPUT"
grep -q '^promotion_writer_identified=1$' <<< "$OUTPUT"
grep -q '^trade_level_verified_net_rows_available=1$' <<< "$OUTPUT"
grep -q '^verified_net_admission_reusable=1$' <<< "$OUTPUT"
grep -q '^policy_config_validated=1$' <<< "$OUTPUT"
grep -q '^policy_loader_reusable=1$' <<< "$OUTPUT"

grep -q '^canonical_trade_level_adapter_excluded=1$' <<< "$OUTPUT"
grep -q '^true_gross_required=0$' <<< "$OUTPUT"

grep -q '^pre_oos_boundary_confirmed=1$' <<< "$OUTPUT"
grep -q '^integration_point_finalized=1$' <<< "$OUTPUT"

grep -q '^reject_action=NO_NEW_OOS_ADMISSION$' <<< "$OUTPUT"
grep -q '^pass_action=EXISTING_OOS_PATH_UNCHANGED$' <<< "$OUTPUT"

grep -q '^enforcement_applied=0$' <<< "$OUTPUT"
grep -q '^production_pipeline_changed=0$' <<< "$OUTPUT"
grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
  '^VERDICT=NET_FIRST_ENFORCEMENT_INSERTION_POINT_FINALIZED$' \
  <<< "$OUTPUT"

echo "VERDICT=TEST_NET_FIRST_ENFORCEMENT_INSERTION_POINT_FINALIZATION_V1_OK"
