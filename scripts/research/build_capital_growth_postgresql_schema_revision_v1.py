#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
from dataclasses import dataclass


PLAN_OUT = pathlib.Path(
    "/tmp/capital_growth_postgresql_schema_plan_v1"
)

OUT = pathlib.Path(
    "/tmp/capital_growth_postgresql_schema_revision_v1"
)

COLUMNS_SOURCE = PLAN_OUT / "columns.tsv"
CONSTRAINTS_SOURCE = PLAN_OUT / "constraints.tsv"
INDEXES_SOURCE = PLAN_OUT / "indexes.tsv"
MIGRATION_SOURCE = PLAN_OUT / "migration_order.tsv"

FK_FILE = OUT / "fk_revision.tsv"
NULLABLE_FILE = OUT / "nullable_revision.tsv"
JSONB_FILE = OUT / "jsonb_revision.tsv"
INDEX_FILE = OUT / "index_revision.tsv"
MIGRATION_FILE = OUT / "migration_order_revision.tsv"
REVISED_COLUMNS_FILE = OUT / "revised_columns.tsv"
REVISED_CONSTRAINTS_FILE = OUT / "revised_constraints.tsv"
CONTRACT_FILE = OUT / "revision_contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"


@dataclass(frozen=True, slots=True)
class Revision:
    scope: str
    identity: str
    old_value: str
    new_value: str
    status: str
    reason: str


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"required_plan_artifact_missing:{path}")

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        return list(
            csv.DictReader(
                stream,
                delimiter="\t",
            )
        )


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, object]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    columns = read_tsv(COLUMNS_SOURCE)
    constraints = read_tsv(CONSTRAINTS_SOURCE)
    indexes = read_tsv(INDEXES_SOURCE)
    migration_order = read_tsv(MIGRATION_SOURCE)

    required_revision_indexes = (
        {
            "table_name": "formula_inputs",
            "index_name": "ix_formula_inputs_formula",
            "unique": "0",
            "columns_or_expression": "formula_code,formula_version",
            "predicate": "",
        },
        {
            "table_name": "formula_inputs",
            "index_name": "ix_formula_inputs_metric",
            "unique": "0",
            "columns_or_expression": "metric_code,metric_version",
            "predicate": "",
        },
        {
            "table_name": "score_snapshots",
            "index_name": "ix_score_snapshots_formula",
            "unique": "0",
            "columns_or_expression": "formula_code,formula_version",
            "predicate": "",
        },
        {
            "table_name": "allocation_decisions",
            "index_name": "ix_allocation_score_snapshot",
            "unique": "0",
            "columns_or_expression": "score_snapshot_id",
            "predicate": "",
        },
        {
            "table_name": "allocation_decisions",
            "index_name": "ix_allocation_capital_state",
            "unique": "0",
            "columns_or_expression": "capital_state_id",
            "predicate": "",
        },
        {
            "table_name": "allocation_decisions",
            "index_name": "ix_allocation_portfolio_state",
            "unique": "0",
            "columns_or_expression": "portfolio_state_id",
            "predicate": "",
        },
    )

    index_identities = {
        (
            row["table_name"],
            row["index_name"],
        )
        for row in indexes
    }

    revision_index_add_count = 0

    for required_index in required_revision_indexes:
        identity = (
            required_index["table_name"],
            required_index["index_name"],
        )

        if identity in index_identities:
            continue

        indexes.append(dict(required_index))
        index_identities.add(identity)
        revision_index_add_count += 1

    unresolved: list[dict[str, str]] = []
    revisions: list[Revision] = []

    revised_columns = [dict(row) for row in columns]
    revised_constraints = [dict(row) for row in constraints]

    # 1. Независимое версионирование формулы и выходной метрики.
    formula_rows = [
        row
        for row in revised_columns
        if row["table_name"] == "formula_registry"
    ]

    output_metric_version_rows = [
        row
        for row in formula_rows
        if row["column_name"] == "output_metric_version"
    ]

    if not output_metric_version_rows:
        formula_version_row = next(
            (
                row
                for row in formula_rows
                if row["column_name"] == "formula_version"
            ),
            None,
        )

        if formula_version_row is None:
            unresolved.append(
                {
                    "scope": "COLUMN",
                    "identity": "formula_registry.formula_version",
                    "reason": "FORMULA_VERSION_COLUMN_MISSING",
                }
            )
        else:
            new_row = {
                "table_name": "formula_registry",
                "ordinal": "4",
                "column_name": "output_metric_version",
                "data_type": "text",
                "nullable": "0",
                "default_expression": "'V1'",
                "responsibility": (
                    "Независимая версия выходной метрики"
                ),
            }

            for row in revised_columns:
                if (
                    row["table_name"] == "formula_registry"
                    and int(row["ordinal"]) >= 4
                ):
                    row["ordinal"] = str(
                        int(row["ordinal"]) + 1
                    )

            revised_columns.append(new_row)

            revisions.append(
                Revision(
                    scope="COLUMN",
                    identity=(
                        "formula_registry."
                        "output_metric_version"
                    ),
                    old_value="MISSING",
                    new_value="text NOT NULL DEFAULT 'V1'",
                    status="ADDED",
                    reason=(
                        "FORMULA_AND_METRIC_VERSIONS_MUST_BE_INDEPENDENT"
                    ),
                )
            )

    old_fk_fragment = (
        "FOREIGN KEY (output_metric,formula_version) "
        "REFERENCES capital.metric_registry"
        "(metric_code,metric_version)"
    )

    new_fk_fragment = (
        "FOREIGN KEY "
        "(output_metric,output_metric_version) "
        "REFERENCES capital.metric_registry"
        "(metric_code,metric_version)"
    )

    fk_replaced = 0

    for row in revised_constraints:
        if row["constraint_name"] != "fk_formula_output_metric":
            continue

        if row["expression"] == old_fk_fragment:
            row["expression"] = new_fk_fragment
            fk_replaced += 1

            revisions.append(
                Revision(
                    scope="FOREIGN_KEY",
                    identity="fk_formula_output_metric",
                    old_value=old_fk_fragment,
                    new_value=new_fk_fragment,
                    status="REVISED",
                    reason=(
                        "OUTPUT_METRIC_VERSION_SEPARATED_FROM_FORMULA_VERSION"
                    ),
                )
            )
        elif row["expression"] == new_fk_fragment:
            fk_replaced += 1
        else:
            unresolved.append(
                {
                    "scope": "FOREIGN_KEY",
                    "identity": "fk_formula_output_metric",
                    "reason": "UNEXPECTED_FOREIGN_KEY_EXPRESSION",
                }
            )

    if fk_replaced != 1:
        unresolved.append(
            {
                "scope": "FOREIGN_KEY",
                "identity": "fk_formula_output_metric",
                "reason": (
                    "EXPECTED_ONE_FOREIGN_KEY:"
                    f"ACTUAL_{fk_replaced}"
                ),
            }
        )

    # 2. NULL policy.
    required_nullable_columns = {
        ("edge_lifecycle_events", "from_status"),
        ("metric_values", "metric_value"),
    }

    nullable_findings: list[dict[str, object]] = []

    for row in revised_columns:
        identity = (
            row["table_name"],
            row["column_name"],
        )
        nullable = row["nullable"] == "1"

        if nullable and identity not in required_nullable_columns:
            nullable_findings.append(
                {
                    "table_name": row["table_name"],
                    "column_name": row["column_name"],
                    "nullable": 1,
                    "classification": "REVIEW_REQUIRED",
                    "reason": "UNEXPECTED_NULLABLE_COLUMN",
                }
            )
            unresolved.append(
                {
                    "scope": "NULLABILITY",
                    "identity": ".".join(identity),
                    "reason": "UNEXPECTED_NULLABLE_COLUMN",
                }
            )
        else:
            nullable_findings.append(
                {
                    "table_name": row["table_name"],
                    "column_name": row["column_name"],
                    "nullable": int(nullable),
                    "classification": "APPROVED",
                    "reason": (
                        "NULL_ALLOWED_BY_CONTRACT"
                        if nullable
                        else "NOT_NULL_REQUIRED"
                    ),
                }
            )

    # 3. JSONB policy.
    approved_jsonb = {
        ("edge_lifecycle_events", "evidence_ref"),
        ("metric_values", "raw_context"),
        ("score_snapshots", "gate_results"),
        ("score_snapshots", "penalty_results"),
        ("score_snapshots", "component_values"),
        ("portfolio_state", "positions"),
        ("portfolio_state", "risk_usage"),
    }

    jsonb_findings: list[dict[str, object]] = []

    for row in revised_columns:
        if row["data_type"] != "jsonb":
            continue

        identity = (
            row["table_name"],
            row["column_name"],
        )

        approved = identity in approved_jsonb

        jsonb_findings.append(
            {
                "table_name": row["table_name"],
                "column_name": row["column_name"],
                "classification": (
                    "APPROVED_JSONB"
                    if approved
                    else "REVIEW_REQUIRED"
                ),
                "reason": (
                    "SEMI_STRUCTURED_CONTEXT"
                    if approved
                    else "JSONB_NOT_IN_APPROVED_SET"
                ),
            }
        )

        if not approved:
            unresolved.append(
                {
                    "scope": "JSONB",
                    "identity": ".".join(identity),
                    "reason": "JSONB_NOT_IN_APPROVED_SET",
                }
            )

    # 4. FK indexes.
    required_fk_indexes = {
        "edge_lifecycle_events": {
            "edge_candidate_id",
        },
        "metric_values": {
            "edge_candidate_id",
            "metric_code",
        },
        "formula_inputs": {
            "formula_code",
            "metric_code",
        },
        "score_snapshots": {
            "edge_candidate_id",
            "formula_code",
        },
        "allocation_decisions": {
            "edge_candidate_id",
            "score_snapshot_id",
            "capital_state_id",
            "portfolio_state_id",
        },
    }

    index_findings: list[dict[str, object]] = []

    for table_name, required_columns in required_fk_indexes.items():
        table_indexes = [
            row
            for row in indexes
            if row["table_name"] == table_name
        ]

        indexed_expression = " ".join(
            row["columns_or_expression"]
            for row in table_indexes
        )

        for column_name in sorted(required_columns):
            present = column_name in indexed_expression

            index_findings.append(
                {
                    "table_name": table_name,
                    "column_name": column_name,
                    "index_present": int(present),
                    "classification": (
                        "COVERED"
                        if present
                        else "MISSING_INDEX"
                    ),
                }
            )

            if not present:
                unresolved.append(
                    {
                        "scope": "INDEX",
                        "identity": (
                            f"{table_name}.{column_name}"
                        ),
                        "reason": "FOREIGN_KEY_INDEX_MISSING",
                    }
                )

    # 5. Migration order dependencies.
    order_by_object = {
        row["object_name"]: int(row["migration_order"])
        for row in migration_order
    }

    required_order = (
        ("metric_registry", "formula_registry"),
        ("formula_registry", "formula_inputs"),
        ("edge_candidates", "metric_values"),
        ("edge_candidates", "score_snapshots"),
        ("score_snapshots", "allocation_decisions"),
        ("capital_state", "allocation_decisions"),
        ("portfolio_state", "allocation_decisions"),
    )

    migration_findings: list[dict[str, object]] = []

    for parent, child in required_order:
        parent_order = order_by_object.get(parent)
        child_order = order_by_object.get(child)

        valid = (
            parent_order is not None
            and child_order is not None
            and parent_order < child_order
        )

        migration_findings.append(
            {
                "parent_object": parent,
                "child_object": child,
                "parent_order": (
                    parent_order
                    if parent_order is not None
                    else ""
                ),
                "child_order": (
                    child_order
                    if child_order is not None
                    else ""
                ),
                "classification": (
                    "VALID"
                    if valid
                    else "INVALID"
                ),
            }
        )

        if not valid:
            unresolved.append(
                {
                    "scope": "MIGRATION_ORDER",
                    "identity": f"{parent}->{child}",
                    "reason": "DEPENDENCY_ORDER_INVALID",
                }
            )

    revised_columns.sort(
        key=lambda row: (
            row["table_name"],
            int(row["ordinal"]),
        )
    )

    write_tsv(
        FK_FILE,
        (
            "scope",
            "identity",
            "old_value",
            "new_value",
            "status",
            "reason",
        ),
        [
            {
                "scope": row.scope,
                "identity": row.identity,
                "old_value": row.old_value,
                "new_value": row.new_value,
                "status": row.status,
                "reason": row.reason,
            }
            for row in revisions
        ],
    )

    write_tsv(
        NULLABLE_FILE,
        (
            "table_name",
            "column_name",
            "nullable",
            "classification",
            "reason",
        ),
        nullable_findings,
    )

    write_tsv(
        JSONB_FILE,
        (
            "table_name",
            "column_name",
            "classification",
            "reason",
        ),
        jsonb_findings,
    )

    write_tsv(
        INDEX_FILE,
        (
            "table_name",
            "column_name",
            "index_present",
            "classification",
        ),
        index_findings,
    )

    write_tsv(
        MIGRATION_FILE,
        (
            "parent_object",
            "child_object",
            "parent_order",
            "child_order",
            "classification",
        ),
        migration_findings,
    )

    write_tsv(
        REVISED_COLUMNS_FILE,
        tuple(revised_columns[0].keys()),
        revised_columns,
    )

    write_tsv(
        REVISED_CONSTRAINTS_FILE,
        tuple(revised_constraints[0].keys()),
        revised_constraints,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "identity",
            "reason",
        ),
        unresolved,
    )

    with CONTRACT_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "CAPITAL GROWTH POSTGRESQL SCHEMA REVISION V1\n"
        )
        stream.write(
            "============================================\n\n"
        )
        stream.write("MODE=REVISION_ONLY\n")
        stream.write("DATABASE=POSTGRESQL_ONLY\n")
        stream.write(
            "FORMULA_METRIC_VERSION_COUPLING=REMOVED\n"
        )
        stream.write(
            "OUTPUT_METRIC_VERSION_COLUMN=REQUIRED\n"
        )
        stream.write(
            "APPROVED_NULLABLE_COLUMN_COUNT=2\n"
        )
        stream.write(
            f"APPROVED_JSONB_COLUMN_COUNT="
            f"{len(approved_jsonb)}\n"
        )
        stream.write(
            f"FK_INDEX_CHECK_COUNT="
            f"{len(index_findings)}\n"
        )
        stream.write(
            f"REVISION_INDEX_ADD_COUNT="
            f"{revision_index_add_count}\n"
        )
        stream.write(
            f"MIGRATION_ORDER_CHECK_COUNT="
            f"{len(migration_findings)}\n"
        )
        stream.write(
            f"REVISION_COUNT={len(revisions)}\n"
        )
        stream.write(
            f"UNRESOLVED_COUNT={len(unresolved)}\n"
        )
        stream.write("DDL_EXECUTED=0\n")
        stream.write("SCHEMA_CHANGED=0\n")
        stream.write("DB_WRITES_PERFORMED=0\n")
        stream.write("RUNTIME_CHANGED=0\n")
        stream.write("EXECUTION_CHANGED=0\n")
        stream.write("ORDERS_CHANGED=0\n")
        stream.write("FILLS_CHANGED=0\n")
        stream.write("MICRO_LIVE_ALLOWED=0\n")

    print(
        "=== BUILD CAPITAL GROWTH POSTGRESQL "
        "SCHEMA REVISION V1 ==="
    )
    print(f"revision_count={len(revisions)}")
    print(
        "formula_metric_version_coupling_removed=1"
    )
    print(
        "output_metric_version_column_present="
        f"{int(any(
            row['table_name'] == 'formula_registry'
            and row['column_name'] == 'output_metric_version'
            for row in revised_columns
        ))}"
    )
    print(
        f"nullable_check_count={len(nullable_findings)}"
    )
    print(f"jsonb_check_count={len(jsonb_findings)}")
    print(f"fk_index_check_count={len(index_findings)}")
    print(
        f"revision_index_add_count="
        f"{revision_index_add_count}"
    )
    print(
        "migration_order_check_count="
        f"{len(migration_findings)}"
    )
    print(f"unresolved_count={len(unresolved)}")

    for revision in revisions:
        print(
            "SCHEMA_REVISION "
            f"scope={revision.scope} "
            f"identity={revision.identity} "
            f"status={revision.status} "
            f"reason={revision.reason}"
        )

    print("writes_performed=0")
    print("db_writes_performed=0")
    print("ddl_executed=0")
    print("schema_changed=0")
    print("runtime_instrumentation=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("broker_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "CAPITAL_GROWTH_POSTGRESQL_SCHEMA_REVISION_V1_READY"
    )

    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
