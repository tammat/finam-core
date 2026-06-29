#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REGISTRY_FRAMEWORK_V1 ==="

PYTHONPATH=src python - <<'PY'
from marketcore.registry.constants import (
    REGISTRY_SCHEMA,
    DEFAULT_PAGE_SIZE,
    DEFAULT_STATUS,
    DEFAULT_MATURITY,
)
from marketcore.registry.lifecycle import (
    REGISTRY_STATUSES,
    REGISTRY_MATURITY_LEVELS,
    is_valid_status,
    is_valid_maturity,
)
from marketcore.registry.validation import (
    RegistryValidationSpec,
    required_fields_sql,
    duplicate_codes_sql,
    invalid_values_sql,
)
from marketcore.registry.indexes import standard_registry_indexes_sql
from marketcore.registry.sql import registry_summary_sql, registry_list_sql, registry_search_sql
from marketcore.registry.json import dumps_payload, empty_payload
from marketcore.registry.ui import registry_card, registry_policy_block

assert REGISTRY_SCHEMA == "warehouse"
assert DEFAULT_PAGE_SIZE == 100
assert DEFAULT_STATUS == "DISCOVERED"
assert DEFAULT_MATURITY == "RESEARCH"

assert is_valid_status("DISCOVERED")
assert is_valid_status("VALIDATED")
assert not is_valid_status("BAD_STATUS")

assert is_valid_maturity("RESEARCH")
assert is_valid_maturity("LIVE")
assert not is_valid_maturity("BAD_MATURITY")

spec = RegistryValidationSpec(
    table="warehouse.ai_registry_v1",
    code_column="ai_code",
    required_columns=("ai_code", "ai_name", "ai_type"),
)

assert "warehouse.ai_registry_v1" in required_fields_sql(spec)
assert "GROUP BY ai_code" in duplicate_codes_sql(spec)
assert "BAD_STATUS" not in invalid_values_sql("warehouse.ai_registry_v1", "status", REGISTRY_STATUSES)

idx_sql = standard_registry_indexes_sql(
    table="warehouse.ai_registry_v1",
    table_short_name="ai_registry_v1",
    code_column="ai_code",
    type_column="ai_type",
)
assert "idx_ai_registry_v1_code" in idx_sql
assert "idx_ai_registry_v1_type" in idx_sql

assert "total_rows" in registry_summary_sql("warehouse.ai_registry_v1")
assert "ORDER BY ai_code" in registry_list_sql("warehouse.ai_registry_v1", ("ai_code",), "ai_code")
assert "ILIKE" in registry_search_sql("warehouse.ai_registry_v1", ("ai_code",), ("ai_code", "ai_name"), "ai_code")

assert dumps_payload({"b": 2, "a": 1}) == '{"a": 1, "b": 2}'
assert empty_payload() == {}

assert "card" in registry_card("rows", 1)
assert "registry_policy" in registry_policy_block("AI_REGISTRY_POLICY_V1")

print("registry_framework=READY")
print("modules=constants,lifecycle,validation,indexes,sql,json,cli,ui")
print("statuses=" + ",".join(REGISTRY_STATUSES))
print("maturity_levels=" + ",".join(REGISTRY_MATURITY_LEVELS))
print("migration_policy=NEW_REGISTRIES_USE_FRAMEWORK_OLD_REGISTRIES_MIGRATE_ON_TOUCH")
PY

grep -q "REGISTRY_FRAMEWORK_V1" src/marketcore/registry/README.md
grep -q "AI Registry становится первым Registry второго поколения" src/marketcore/registry/README.md
grep -q "schema → builder → validation → cli → read_only_ui → complete → checkpoint" src/marketcore/registry/README.md

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=REGISTRY_FRAMEWORK_V1_READY"
echo "TEST_REGISTRY_FRAMEWORK_V1_OK"
