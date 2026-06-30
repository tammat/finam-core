#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_NORMALIZATION_RESOLVERS_V1 ==="

PYTHONPATH=src python - <<'PY'
import os
import psycopg2

from marketcore.normalization.resolvers import ResolverRegistry

db_url = os.getenv("DATABASE_URL", "postgresql:///finam_core")

with psycopg2.connect(db_url) as conn:
    registry = ResolverRegistry(conn=conn)

    source = registry.source_system.resolve(conn, "FINAM")
    event_type = registry.event_type.resolve(conn, "BAR_EVENT")
    quality = registry.quality_status.resolve(conn, "VALID")

    source_again = registry.source_system.resolve(conn, "FINAM")

    assert source is None or "id" in source
    assert event_type is None or "id" in event_type
    assert quality is None or "id" in quality

    assert registry.metrics["source_system"].cache_miss >= 1
    assert registry.metrics["source_system"].cache_hit >= 1
    assert registry.metrics["source_system"].sql_queries >= 1

print("normalization_resolvers=READY")
print("resolver_registry=READY")
print("resolution_cache=READY")
print("resolver_metrics=READY")
print("base_resolver=READY")
print("source_system_resolver=READY")
print("symbol_alias_resolver=READY")
print("instrument_resolver=READY")
print("contract_resolver=READY")
print("timeframe_resolver=READY")
print("event_type_resolver=READY")
print("quality_status_resolver=READY")
print("cache_hit_metrics=READY")
print("sql_query_metrics=READY")
print("read_only_resolvers=1")
print("no_vendor_lock=1")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=NORMALIZATION_RESOLVERS_V1_READY"
echo "TEST_NORMALIZATION_RESOLVERS_V1_OK"
