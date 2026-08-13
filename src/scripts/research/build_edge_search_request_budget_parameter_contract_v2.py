"""Read-only plan V2 для разделения universe capacity и cycle budget."""

from __future__ import annotations

import os

import psycopg2
from psycopg2.extras import RealDictCursor


TABLE = "marketcore_action.edge_search_request_parameter_v1"


def main() -> int:
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema='marketcore_action'
                  AND table_name='edge_search_request_parameter_v1'
                ORDER BY ordinal_position
                """
            )

            columns = list(cur.fetchall())

    names = {
        str(row["column_name"])
        for row in columns
    }

    for row in columns:
        print(
            "PARAMETER_COLUMN "
            f"name={row['column_name']} "
            f"type={row['data_type']} "
            f"nullable={row['is_nullable']} "
            f"default={row['column_default'] or 'NONE'}"
        )

    variant_present = "variant_budget" in names
    cycle_present = "cycle_budget" in names

    print(f"variant_budget_present={int(variant_present)}")
    print(f"cycle_budget_present={int(cycle_present)}")

    if not variant_present:
        raise RuntimeError(
            "REQUEST_BUDGET_V2_VARIANT_BUDGET_MISSING"
        )

    # V2 semantics.
    print("variant_budget_semantics=UNIVERSE_CAPACITY_UPPER_BOUND")
    print("cycle_budget_semantics=TARGETED_CHALLENGERS_PER_CYCLE")
    print("cycle_budget_default_policy=1")
    print("cycle_budget_positive_required=1")
    print("cycle_budget_lte_variant_budget_required=1")

    # Backward compatibility:
    # старые rows без cycle_budget должны интерпретироваться безопасно.
    print("legacy_rows_supported=1")
    print("legacy_cycle_budget_resolution=MIN_1_VARIANT_BUDGET")
    print("variant_budget_column_removed=0")
    print("target_id_changed=0")

    print("schema_changed=0")
    print("parameter_store_changed=0")
    print("worker_transport_changed=0")
    print("optimizer_changed=0")
    print("allocator_changed=0")
    print("db_writes_performed=0")
    print("queue_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "EDGE_SEARCH_REQUEST_BUDGET_PARAMETER_CONTRACT_V2_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
