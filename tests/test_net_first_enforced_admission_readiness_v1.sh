#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
SCRIPT="src/scripts/research/build_net_first_enforced_admission_readiness_v1.py"

echo "=== TEST NET FIRST ENFORCED ADMISSION READINESS V1 ==="

PYTHONPATH=src "$PY" -m py_compile "$SCRIPT"

OUTPUT="$(
    PYTHONPATH=src "$PY" "$SCRIPT"
)"

printf '%s\n' "$OUTPUT"

grep -q '^negative_control_total=3$' <<< "$OUTPUT"
grep -q '^negative_control_reject=3$' <<< "$OUTPUT"
grep -q '^negative_control_robustness_saved=3$' <<< "$OUTPUT"

grep -q '^positive_verified_net_admit=14$' <<< "$OUTPUT"
grep -q '^positive_trade_level_admit=3$' <<< "$OUTPUT"
grep -q '^positive_runner_v2_admit=1$' <<< "$OUTPUT"
grep -q '^positive_control_classes=3$' <<< "$OUTPUT"

grep -q '^shadow_candidates=27$' <<< "$OUTPUT"
grep -q '^shadow_economically_resolved=27$' <<< "$OUTPUT"
grep -q '^shadow_would_admit=18$' <<< "$OUTPUT"
grep -q '^shadow_would_reject=9$' <<< "$OUTPUT"
grep -q '^shadow_coverage_pct=100.0000$' <<< "$OUTPUT"

grep -q '^economic_gate_before_robustness=1$' <<< "$OUTPUT"
grep -q '^strategy_specific_logic_used=0$' <<< "$OUTPUT"
grep -q '^policy_from_config=1$' <<< "$OUTPUT"

grep -q '^economic_admission_scope_only=1$' <<< "$OUTPUT"
grep -q '^robustness_gate_still_required=1$' <<< "$OUTPUT"
grep -q '^oos_gate_still_required=1$' <<< "$OUTPUT"

grep -q '^enforced_admission_enabled=0$' <<< "$OUTPUT"
grep -q '^production_pipeline_changed=0$' <<< "$OUTPUT"
grep -q '^db_writes_performed=0$' <<< "$OUTPUT"
grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
  '^VERDICT=NET_FIRST_ENFORCED_ADMISSION_READINESS_V1_READY$' \
  <<< "$OUTPUT"

echo "readiness_fail_closed=1"
echo "enforcement_applied=0"
echo "VERDICT=TEST_NET_FIRST_ENFORCED_ADMISSION_READINESS_V1_OK"
