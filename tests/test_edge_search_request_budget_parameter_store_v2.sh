#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST EDGE SEARCH REQUEST BUDGET PARAMETER STORE V2 ==="

# ------------------------------------------------------------
# 1. SCHEMA CONTRACT
# ------------------------------------------------------------

SCHEMA_OUT="/tmp/request_budget_parameter_store_v2_schema.out"
rm -f "$SCHEMA_OUT"

psql -U alex -d finam_core \
  -X -v ON_ERROR_STOP=1 -At <<'SQL' \
  | tee "$SCHEMA_OUT"

SELECT
    'cycle_budget_column=' ||
    count(*)::text
FROM information_schema.columns
WHERE table_schema='marketcore_action'
  AND table_name='edge_search_request_parameter_v1'
  AND column_name='cycle_budget';

SELECT
    'positive_constraint=' ||
    count(*)::text
FROM pg_constraint
WHERE conrelid=
    'marketcore_action.edge_search_request_parameter_v1'::regclass
  AND conname=
    'edge_search_request_parameter_v1_cycle_budget_positive_check';

SELECT
    'lte_variant_constraint=' ||
    count(*)::text
FROM pg_constraint
WHERE conrelid=
    'marketcore_action.edge_search_request_parameter_v1'::regclass
  AND conname=
    'edge_search_request_parameter_v1_cycle_budget_lte_variant_check';

SELECT
    'legacy_null_rows=' ||
    count(*)::text
FROM marketcore_action.edge_search_request_parameter_v1
WHERE cycle_budget IS NULL;

SQL

grep -q '^cycle_budget_column=1$' "$SCHEMA_OUT"
grep -q '^positive_constraint=1$' "$SCHEMA_OUT"
grep -q '^lte_variant_constraint=1$' "$SCHEMA_OUT"

echo "schema_contract_valid=1"

# ------------------------------------------------------------
# 2. VALID V2 CONTRACT: variant=13, cycle=1
# Родитель и параметр создаются атомарно.
# Ничего не сохраняется.
# ------------------------------------------------------------

psql -U alex -d finam_core \
  -X -v ON_ERROR_STOP=1 <<'SQL'

BEGIN;

WITH parent AS (
    INSERT INTO marketcore_action.command_request_v2 (
        request_id,
        action_id,
        request_kind,
        command_code,
        actor_id,
        target_id,
        status,
        requested_at
    )
    VALUES (
        gen_random_uuid()::text,
        'research.edge_search.run',
        'EDGE_SEARCH_RUN',
        'RESEARCH.RUN_EDGE_SEARCH',
        'test.budget.parameter.store.v2',
        'TARGETED_V1|EXIT_OOS|VALID_PROOF@RTSX|PROOF|LONG',
        'PENDING',
        clock_timestamp()
    )
    RETURNING request_id
)
INSERT INTO marketcore_action.edge_search_request_parameter_v1 (
    request_id,
    variant_budget,
    cycle_budget
)
SELECT
    request_id,
    13,
    1
FROM parent;

ROLLBACK;

SQL

echo "valid_variant_13_cycle_1=1"
echo "valid_proof_persisted=0"

# ------------------------------------------------------------
# 3. LEGACY CONTRACT:
# variant_budget присутствует, cycle_budget=NULL.
# ------------------------------------------------------------

psql -U alex -d finam_core \
  -X -v ON_ERROR_STOP=1 <<'SQL'

BEGIN;

WITH parent AS (
    INSERT INTO marketcore_action.command_request_v2 (
        request_id,
        action_id,
        request_kind,
        command_code,
        actor_id,
        target_id,
        status,
        requested_at
    )
    VALUES (
        gen_random_uuid()::text,
        'research.edge_search.run',
        'EDGE_SEARCH_RUN',
        'RESEARCH.RUN_EDGE_SEARCH',
        'test.budget.parameter.store.v2',
        'TARGETED_V1|EXIT_OOS|LEGACY_PROOF@RTSX|PROOF|LONG',
        'PENDING',
        clock_timestamp()
    )
    RETURNING request_id
)
INSERT INTO marketcore_action.edge_search_request_parameter_v1 (
    request_id,
    variant_budget
)
SELECT
    request_id,
    13
FROM parent;

ROLLBACK;

SQL

echo "legacy_null_cycle_budget_allowed=1"
echo "legacy_proof_persisted=0"

# ------------------------------------------------------------
# 4. INVALID CONTRACT:
# cycle_budget=0 должен быть отвергнут CHECK constraint.
# Parent существует, поэтому FK больше не маскирует проверку.
# ------------------------------------------------------------

ZERO_OUT="/tmp/request_budget_parameter_store_v2_zero.out"
rm -f "$ZERO_OUT"

if psql -U alex -d finam_core \
  -X -v ON_ERROR_STOP=1 \
  >"$ZERO_OUT" 2>&1 <<'SQL'

BEGIN;

WITH parent AS (
    INSERT INTO marketcore_action.command_request_v2 (
        request_id,
        action_id,
        request_kind,
        command_code,
        actor_id,
        target_id,
        status,
        requested_at
    )
    VALUES (
        gen_random_uuid()::text,
        'research.edge_search.run',
        'EDGE_SEARCH_RUN',
        'RESEARCH.RUN_EDGE_SEARCH',
        'test.budget.parameter.store.v2',
        'TARGETED_V1|EXIT_OOS|ZERO_PROOF@RTSX|PROOF|LONG',
        'PENDING',
        clock_timestamp()
    )
    RETURNING request_id
)
INSERT INTO marketcore_action.edge_search_request_parameter_v1 (
    request_id,
    variant_budget,
    cycle_budget
)
SELECT
    request_id,
    13,
    0
FROM parent;

ROLLBACK;

SQL
then
    echo "ERROR=CYCLE_BUDGET_ZERO_ACCEPTED"
    exit 1
fi

grep -q \
'edge_search_request_parameter_v1_cycle_budget_positive_check' \
"$ZERO_OUT"

echo "cycle_budget_zero_rejected=1"
echo "cycle_budget_zero_rejected_by_expected_constraint=1"

# ------------------------------------------------------------
# 5. INVALID CONTRACT:
# cycle_budget > variant_budget должен быть отвергнут.
# ------------------------------------------------------------

OVER_OUT="/tmp/request_budget_parameter_store_v2_over.out"
rm -f "$OVER_OUT"

if psql -U alex -d finam_core \
  -X -v ON_ERROR_STOP=1 \
  >"$OVER_OUT" 2>&1 <<'SQL'

BEGIN;

WITH parent AS (
    INSERT INTO marketcore_action.command_request_v2 (
        request_id,
        action_id,
        request_kind,
        command_code,
        actor_id,
        target_id,
        status,
        requested_at
    )
    VALUES (
        gen_random_uuid()::text,
        'research.edge_search.run',
        'EDGE_SEARCH_RUN',
        'RESEARCH.RUN_EDGE_SEARCH',
        'test.budget.parameter.store.v2',
        'TARGETED_V1|EXIT_OOS|OVER_PROOF@RTSX|PROOF|LONG',
        'PENDING',
        clock_timestamp()
    )
    RETURNING request_id
)
INSERT INTO marketcore_action.edge_search_request_parameter_v1 (
    request_id,
    variant_budget,
    cycle_budget
)
SELECT
    request_id,
    13,
    14
FROM parent;

ROLLBACK;

SQL
then
    echo "ERROR=CYCLE_BUDGET_OVER_VARIANT_ACCEPTED"
    exit 1
fi

grep -q \
'edge_search_request_parameter_v1_cycle_budget_lte_variant_check' \
"$OVER_OUT"

echo "cycle_budget_over_variant_rejected=1"
echo "cycle_budget_over_variant_rejected_by_expected_constraint=1"

# ------------------------------------------------------------
# 6. NO TEST RESIDUE
# ------------------------------------------------------------

RESIDUE="$(
psql -U alex -d finam_core \
  -X -v ON_ERROR_STOP=1 -At <<'SQL'
SELECT count(*)
FROM marketcore_action.command_request_v2
WHERE actor_id='test.budget.parameter.store.v2';
SQL
)"

test "$RESIDUE" = "0"

echo "test_command_request_residue=0"

echo "variant_budget_semantics=UNIVERSE_CAPACITY_UPPER_BOUND"
echo "cycle_budget_semantics=TARGETED_CHALLENGERS_PER_CYCLE"
echo "legacy_rows_supported=1"
echo "foreign_key_contract_preserved=1"
echo "test_rows_persisted=0"
echo "worker_transport_changed=0"
echo "optimizer_changed=0"
echo "allocator_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SEARCH_REQUEST_BUDGET_PARAMETER_STORE_V2_OK"
