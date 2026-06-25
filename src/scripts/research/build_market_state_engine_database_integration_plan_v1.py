#!/usr/bin/env python3

# ==========================================================
# MARKET_STATE_ENGINE_DATABASE_INTEGRATION_PLAN_V1
#
# План интеграции Market State Engine с PostgreSQL.
#
# ВАЖНО:
# - это НЕ миграция БД;
# - это НЕ запись данных;
# - Runtime не изменяется;
# - Execution не изменяется;
# - реальные заявки не отправляются.
# ==========================================================

print("=== MARKET_STATE_ENGINE_DATABASE_INTEGRATION_PLAN_V1 ===")
print("mode=database_integration_plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

print("\nTARGET_TABLES")
tables = [
    "research.market_state_snapshots_v1",
    "research.market_state_snapshot_values_v1",
    "research.market_state_snapshot_metadata_v1",
    "research.market_state_transitions_v1",
]
for table in tables:
    print(f"TABLE name={table}")

print("\nWRITE_FLOW")
flow = [
    ("MarketStateBuiltEvent", "получить событие построенного состояния рынка"),
    ("SnapshotWriter", "сохранить snapshot header"),
    ("SnapshotValueWriter", "сохранить значения состояний"),
    ("SnapshotMetadataWriter", "сохранить версии классификаторов, онтологии и research"),
    ("TransitionWriter", "сохранить переход состояния при наличии предыдущего snapshot"),
]
for step, desc in flow:
    print(f"FLOW_STEP name={step} description_ru={desc}")

print("\nFILE_STRUCTURE")
files = [
    "src/finam_core/research/market_state/storage.py",
    "src/finam_core/research/market_state/repository.py",
    "src/finam_core/research/market_state/db_writer.py",
    "scripts/test_market_state_engine_database_integration_plan_v1.sh",
]
for file in files:
    print(f"FILE path={file}")

print("\nSAFETY_GUARDS")
guards = [
    "postgres_only",
    "no_sqlite",
    "no_runtime_write",
    "no_execution_write",
    "no_order_client_import",
    "no_broker_adapter_import",
    "idempotent_insert_required",
    "transaction_required",
    "rollback_on_error_required",
]
for guard in guards:
    print(f"GUARD name={guard}")

print("\nDESIGN_RULES")
rules = [
    "database_integration_is_research_only",
    "market_state_snapshot_is_immutable",
    "snapshot_values_are_rows",
    "metadata_versions_required",
    "canonical_signature_required",
    "compact_signature_required",
    "no_runtime_execution_changes",
]
for rule in rules:
    print(f"rule={rule}")

print("\nNEXT_STEPS")
print("next=MARKET_STATE_ENGINE_DATABASE_SCHEMA_DRY_RUN_V1")
print("next=MARKET_STATE_ENGINE_DATABASE_WRITER_IMPLEMENTATION_V1")

print("\nVERDICT=MARKET_STATE_ENGINE_DATABASE_INTEGRATION_PLAN_READY")
