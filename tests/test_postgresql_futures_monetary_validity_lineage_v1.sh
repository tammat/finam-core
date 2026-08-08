#!/usr/bin/env bash
set -euo pipefail

SCRIPT="scripts/research/build_postgresql_futures_monetary_validity_lineage_v1.py"

echo "=== TEST_POSTGRESQL_FUTURES_MONETARY_VALIDITY_LINEAGE_V1 ==="

python -m py_compile "$SCRIPT"

OUTPUT="$(PYTHONPATH=src python "$SCRIPT")"

printf '%s\n' "$OUTPUT"

grep -q '^total_runs=73$' <<<"$OUTPUT"
grep -q '^valid_monetary_runs=1$' <<<"$OUTPUT"
grep -q '^valid_monetary_trades=167$' <<<"$OUTPUT"

grep -q '^legacy_invalid_monetary_runs=12$' <<<"$OUTPUT"
grep -q '^legacy_invalid_monetary_trades=6223$' <<<"$OUTPUT"

grep -q '^unresolved_no_spec_runs=36$' <<<"$OUTPUT"
grep -q '^unresolved_no_spec_trades=34005$' <<<"$OUTPUT"

grep -q '^unresolved_cbr_monetary_runs=24$' <<<"$OUTPUT"
grep -q '^unresolved_cbr_monetary_trades=9985$' <<<"$OUTPUT"

grep -q '^ranking_allowed_runs=1$' <<<"$OUTPUT"
grep -q '^fail_closed=1$' <<<"$OUTPUT"
grep -q '^db_writes_performed=0$' <<<"$OUTPUT"
grep -q '^runtime_changed=0$' <<<"$OUTPUT"
grep -q '^execution_changed=0$' <<<"$OUTPUT"
grep -q '^orders_changed=0$' <<<"$OUTPUT"
grep -q '^fills_changed=0$' <<<"$OUTPUT"
grep -q '^micro_live_allowed=0$' <<<"$OUTPUT"

grep -q \
  'run_uuid=3df90793-7237-4024-bcd9-08866146e93f .*monetary_status=VALID_MONETARY .*ranking_allowed=1' \
  <<<"$OUTPUT"

echo \
  "VERDICT=TEST_POSTGRESQL_FUTURES_MONETARY_VALIDITY_LINEAGE_V1_OK"
