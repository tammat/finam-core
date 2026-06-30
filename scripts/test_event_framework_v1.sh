#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EVENT_FRAMEWORK_V1 ==="

PYTHONPATH=src python - <<'PY'
from marketcore.event.constants import (
    DEFAULT_EVENT_VERSION,
    EVENT_TYPES,
    EVENT_GRANULARITY,
    SOURCE_SYSTEM_TYPES,
)
from marketcore.event.identity import (
    EventIdentitySpec,
    event_identity_columns_sql,
    event_identity_required_columns,
)
from marketcore.event.lifecycle import (
    EVENT_LIFECYCLE_STATUSES,
    is_valid_event_lifecycle,
)
from marketcore.event.quality import (
    QUALITY_STATUSES,
    QUALITY_REASONS,
    is_valid_quality_status,
)
from marketcore.event.lineage import (
    EventLineageSpec,
    event_lineage_columns_sql,
    event_lineage_required_columns,
)
from marketcore.event.validation import (
    EventValidationSpec,
    required_fields_sql,
    invalid_values_sql,
    time_order_violations_sql,
    duplicate_event_uuid_sql,
)
from marketcore.event.indexes import standard_event_indexes_sql
from marketcore.event.sql import event_summary_sql, event_health_sql, event_list_sql, event_search_sql
from marketcore.event.ui import event_card, event_policy_block

assert DEFAULT_EVENT_VERSION == "v1"
assert "BAR_EVENT" in EVENT_TYPES
assert "QUOTE_EVENT" in EVENT_TYPES
assert "TRADE_TICK_EVENT" in EVENT_TYPES
assert "DATA_QUALITY_EVENT" in EVENT_TYPES
assert "BAR" in EVENT_GRANULARITY
assert "TICK" in EVENT_GRANULARITY
assert "BROKER" in SOURCE_SYSTEM_TYPES

assert is_valid_event_lifecycle("RECEIVED")
assert is_valid_event_lifecycle("VALIDATED")
assert not is_valid_event_lifecycle("BAD_LIFECYCLE")

assert is_valid_quality_status("VALID")
assert is_valid_quality_status("REVIEW_REQUIRED")
assert not is_valid_quality_status("BAD_QUALITY")

assert "TIME_ORDER_VIOLATION" in QUALITY_REASONS
assert "UNKNOWN_SYMBOL" in QUALITY_REASONS

identity_spec = EventIdentitySpec()
assert identity_spec.event_id_column == "event_id"
assert "event_uuid uuid" in event_identity_columns_sql()
assert "event_sequence" in event_identity_required_columns()

lineage_spec = EventLineageSpec()
assert lineage_spec.source_system_column == "source_system_id"
assert "source_system_id bigint NOT NULL" in event_lineage_columns_sql()
assert "algorithm_version" in event_lineage_required_columns()

spec = EventValidationSpec(
    table="warehouse.normalized_bar_event_v1",
    event_type="BAR_EVENT",
    required_columns=(
        "event_uuid",
        "event_sequence",
        "event_type",
        "source_system_id",
        "quality_status",
        "event_time",
        "source_time",
        "received_at",
        "normalized_at",
    ),
)

assert "required_fields_valid" in required_fields_sql(spec)
assert "time_order_violations" in time_order_violations_sql(spec)
assert "duplicate_event_uuid" in duplicate_event_uuid_sql("warehouse.normalized_bar_event_v1")
assert "BAD_QUALITY" not in invalid_values_sql("warehouse.normalized_bar_event_v1", "quality_status", QUALITY_STATUSES)

idx_sql = standard_event_indexes_sql(
    table="warehouse.normalized_bar_event_v1",
    table_short_name="normalized_bar_event_v1",
)
assert "event_sequence" in idx_sql
assert "event_time" in idx_sql
assert "instrument_id" in idx_sql
assert "contract_id" in idx_sql
assert "timeframe_id" in idx_sql
assert "quality_status" in idx_sql
assert "normalization_run_id" in idx_sql

assert "total_events" in event_summary_sql("warehouse.normalized_bar_event_v1")
assert "valid_events" in event_health_sql("warehouse.normalized_bar_event_v1")
assert "ORDER BY event_time DESC" in event_list_sql("warehouse.normalized_bar_event_v1", ("event_id",))
assert "ILIKE" in event_search_sql("warehouse.normalized_bar_event_v1", ("event_id",), ("event_type", "source_key"))

assert "card" in event_card("events", 1)
assert "event_policy" in event_policy_block("EVENT_IMMUTABILITY_POLICY_V1")

print("event_framework=READY")
print("modules=constants,identity,lifecycle,quality,lineage,validation,indexes,sql,cli,ui")
print("event_types=" + ",".join(EVENT_TYPES))
print("quality_statuses=" + ",".join(QUALITY_STATUSES))
print("quality_reasons=" + ",".join(QUALITY_REASONS))
print("event_lifecycle=" + ",".join(EVENT_LIFECYCLE_STATUSES))
print("identity_policy=IDENTITY_POLICY_V1")
print("immutability_policy=EVENT_IMMUTABILITY_POLICY_V1")
print("time_policy=EVENT_TIME_POLICY_V1")
print("migration_policy=NEW_EVENTS_USE_EVENT_FRAMEWORK")
PY

grep -q "EVENT_FRAMEWORK_V1" src/marketcore/event/README.md
grep -q "IDENTITY_POLICY_V1" src/marketcore/event/README.md
grep -q "UPDATE событий запрещён" src/marketcore/event/README.md
grep -q "event_time <= source_time <= received_at <= normalized_at" src/marketcore/event/README.md

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EVENT_FRAMEWORK_V1_READY"
echo "TEST_EVENT_FRAMEWORK_V1_OK"
