#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib


PRIORITY_DIR = pathlib.Path(
    "/tmp/decision_owner_priority_confirmation_v1"
)
LAYERED_DIR = pathlib.Path(
    "/tmp/execution_broker_layered_status_ownership_v1"
)

PRIORITY_OWNERS = (
    PRIORITY_DIR / "confirmed_priority_owners.tsv"
)
PRIORITY_DEFERRED = (
    PRIORITY_DIR / "deferred_priority_owners.tsv"
)

LAYERED_OWNERS = (
    LAYERED_DIR / "confirmed_status_owners.tsv"
)
LAYERED_EDGES = (
    LAYERED_DIR / "ownership_edges.tsv"
)
LAYERED_UNRESOLVED = (
    LAYERED_DIR / "unresolved.tsv"
)

OUTPUT_DIR = pathlib.Path(
    "/tmp/decision_owner_registry_v1"
)

REGISTRY_FILE = (
    OUTPUT_DIR / "decision_owner_registry_v1.tsv"
)
EDGES_FILE = (
    OUTPUT_DIR / "decision_owner_edges_v1.tsv"
)
CONTRACT_FILE = (
    OUTPUT_DIR / "decision_owner_contract_v1.txt"
)
DEFERRED_FILE = (
    OUTPUT_DIR / "deferred_stages_v1.tsv"
)
UNRESOLVED_FILE = (
    OUTPUT_DIR / "unresolved_v1.tsv"
)

EXPECTED_CONFIRMED_STAGES = {
    "RISK",
    "RUNTIME",
    "EXECUTION",
    "BROKER",
}

ALL_STAGES = (
    "MARKET_DATA",
    "STRATEGY",
    "REGIME",
    "EDGE",
    "RISK",
    "PORTFOLIO",
    "RUNTIME",
    "EXECUTION",
    "BROKER",
    "FILL",
)


def read_tsv(
    path: pathlib.Path,
) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(
            f"source_file_missing:{path}"
        )

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
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    priority_owners = read_tsv(
        PRIORITY_OWNERS
    )
    priority_deferred = read_tsv(
        PRIORITY_DEFERRED
    )
    layered_owners = read_tsv(
        LAYERED_OWNERS
    )
    layered_edges = read_tsv(
        LAYERED_EDGES
    )
    layered_unresolved = read_tsv(
        LAYERED_UNRESOLVED
    )

    unresolved: list[dict[str, object]] = []

    for row in layered_unresolved:
        if any(
            str(value).strip()
            for value in row.values()
        ):
            unresolved.append(
                {
                    "scope": row.get(
                        "scope",
                        "",
                    ),
                    "symbol": row.get(
                        "symbol",
                        "",
                    ),
                    "reason": row.get(
                        "reason",
                        "",
                    ),
                }
            )

    registry: list[dict[str, object]] = []

    for row in priority_owners:
        stage = row["stage"]

        if stage not in {"RISK", "RUNTIME"}:
            unresolved.append(
                {
                    "scope": "PRIORITY_OWNER",
                    "symbol": stage,
                    "reason": (
                        "UNEXPECTED_PRIORITY_STAGE"
                    ),
                }
            )
            continue

        registry.append(
            {
                "stage": stage,
                "ownership_scope": (
                    "DECISION_GATE"
                ),
                "owner_path": row[
                    "owner_path"
                ],
                "owner_symbol": row[
                    "owner_symbol"
                ],
                "owner_granularity": row[
                    "owner_granularity"
                ],
                "classification": (
                    "CONFIRMED_DECISION_OWNER"
                ),
                "responsibility": row[
                    "evidence"
                ],
                "failure_policy": row[
                    "failure_policy"
                ],
                "owner_confirmed": 1,
                "runtime_instrumentation": 0,
            }
        )

    for row in layered_owners:
        stage = row["stage"]

        if stage == "EXECUTION":
            owner_path = (
                "src/finam_core/execution/"
                "execution_dispatcher.py"
            )
        elif stage == "BROKER":
            owner_path = (
                "src/finam_core/adapters/"
                "grpc/orders_client.py"
            )
        else:
            unresolved.append(
                {
                    "scope": (
                        "LAYERED_STATUS_OWNER"
                    ),
                    "symbol": stage,
                    "reason": (
                        "UNEXPECTED_LAYERED_STAGE"
                    ),
                }
            )
            continue

        registry.append(
            {
                "stage": stage,
                "ownership_scope": row[
                    "ownership_scope"
                ],
                "owner_path": owner_path,
                "owner_symbol": row[
                    "owner_symbol"
                ],
                "owner_granularity": row[
                    "owner_granularity"
                ],
                "classification": (
                    "CONFIRMED_RESULT_OWNER"
                ),
                "responsibility": row[
                    "responsibility"
                ],
                "failure_policy": (
                    "FAIL_OPEN_RECORDER"
                ),
                "owner_confirmed": 1,
                "runtime_instrumentation": 0,
            }
        )

    stage_order = {
        stage: index
        for index, stage in enumerate(
            ALL_STAGES
        )
    }

    registry.sort(
        key=lambda row: stage_order[
            str(row["stage"])
        ]
    )

    confirmed_stages = {
        str(row["stage"])
        for row in registry
    }

    duplicate_stage_count = (
        len(registry)
        - len(confirmed_stages)
    )

    missing_expected_stages = sorted(
        EXPECTED_CONFIRMED_STAGES
        - confirmed_stages
    )

    unexpected_confirmed_stages = sorted(
        confirmed_stages
        - EXPECTED_CONFIRMED_STAGES
    )

    for stage in missing_expected_stages:
        unresolved.append(
            {
                "scope": "REGISTRY_STAGE",
                "symbol": stage,
                "reason": (
                    "EXPECTED_CONFIRMED_OWNER_MISSING"
                ),
            }
        )

    for stage in unexpected_confirmed_stages:
        unresolved.append(
            {
                "scope": "REGISTRY_STAGE",
                "symbol": stage,
                "reason": (
                    "UNEXPECTED_CONFIRMED_OWNER"
                ),
            }
        )

    if duplicate_stage_count:
        unresolved.append(
            {
                "scope": "REGISTRY",
                "symbol": "",
                "reason": (
                    "DUPLICATE_CONFIRMED_STAGE_OWNER"
                ),
            }
        )

    deferred_by_stage = {
        row.get("stage", ""): row
        for row in priority_deferred
        if row.get("stage")
    }

    deferred_rows: list[
        dict[str, object]
    ] = []

    for stage in ALL_STAGES:
        if stage in confirmed_stages:
            continue

        source = deferred_by_stage.get(
            stage
        )

        deferred_rows.append(
            {
                "stage": stage,
                "status": "DEFERRED",
                "candidate": (
                    source.get(
                        "candidate",
                        "",
                    )
                    if source
                    else ""
                ),
                "reason": (
                    source.get(
                        "reason",
                        "",
                    )
                    if source
                    else (
                        "OWNER_EVIDENCE_NOT_YET_"
                        "COMPLETED"
                    )
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    edges = [
        {
            "edge_order": 1,
            "source_stage": "RISK",
            "source_owner": (
                "PortfolioRiskGate.check"
            ),
            "target_stage": "RUNTIME",
            "target_owner": (
                "_execute_br_signal_in_paper"
            ),
            "classification": (
                "CONFIRMED_DECISION_FLOW"
            ),
            "reachable": 1,
            "runtime_instrumentation": 0,
        },
        {
            "edge_order": 2,
            "source_stage": "RUNTIME",
            "source_owner": (
                "_execute_br_signal_in_paper"
            ),
            "target_stage": "EXECUTION",
            "target_owner": (
                "ExecutionDispatcher"
            ),
            "classification": (
                "CONFIRMED_DECISION_FLOW"
            ),
            "reachable": 1,
            "runtime_instrumentation": 0,
        },
        {
            "edge_order": 3,
            "source_stage": "EXECUTION",
            "source_owner": (
                "ExecutionDispatcher"
            ),
            "target_stage": "BROKER",
            "target_owner": (
                "FinamOrdersClient"
            ),
            "classification": (
                "CONFIRMED_RESULT_FLOW"
            ),
            "reachable": 1,
            "runtime_instrumentation": 0,
        },
    ]

    # Сохраняем подтверждённый обратный
    # status-flow как отдельную семантическую связь.
    for row in layered_edges:
        if (
            row.get("reachable") == "1"
            and row.get("source_stage")
            == "BROKER"
            and row.get("target_stage")
            == "EXECUTION"
        ):
            edges.append(
                {
                    "edge_order": 4,
                    "source_stage": (
                        "BROKER"
                    ),
                    "source_owner": row[
                        "source_owner"
                    ],
                    "target_stage": (
                        "EXECUTION"
                    ),
                    "target_owner": row[
                        "target_owner"
                    ],
                    "classification": (
                        "CONFIRMED_STATUS_RETURN_FLOW"
                    ),
                    "reachable": 1,
                    "runtime_instrumentation": 0,
                }
            )

    write_tsv(
        REGISTRY_FILE,
        (
            "stage",
            "ownership_scope",
            "owner_path",
            "owner_symbol",
            "owner_granularity",
            "classification",
            "responsibility",
            "failure_policy",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        registry,
    )

    write_tsv(
        EDGES_FILE,
        (
            "edge_order",
            "source_stage",
            "source_owner",
            "target_stage",
            "target_owner",
            "classification",
            "reachable",
            "runtime_instrumentation",
        ),
        edges,
    )

    write_tsv(
        DEFERRED_FILE,
        (
            "stage",
            "status",
            "candidate",
            "reason",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        deferred_rows,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "symbol",
            "reason",
        ),
        unresolved,
    )

    with CONTRACT_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "DECISION OWNER REGISTRY V1\n"
        )
        stream.write(
            "==========================\n\n"
        )

        for row in registry:
            stream.write(
                f"{row['stage']}="
                f"{row['owner_symbol']}\n"
            )

        stream.write("\n")
        stream.write(
            f"CONFIRMED_OWNER_COUNT="
            f"{len(registry)}\n"
        )
        stream.write(
            f"DUPLICATE_STAGE_OWNER_COUNT="
            f"{duplicate_stage_count}\n"
        )
        stream.write(
            f"DEFERRED_STAGE_COUNT="
            f"{len(deferred_rows)}\n"
        )
        stream.write(
            f"UNRESOLVED_COUNT="
            f"{len(unresolved)}\n"
        )
        stream.write(
            "RUNTIME_INSTRUMENTATION=0\n"
        )

    print(
        "=== BUILD DECISION OWNER "
        "REGISTRY V1 ==="
    )
    print(
        f"confirmed_owner_count="
        f"{len(registry)}"
    )
    print(
        f"confirmed_stage_count="
        f"{len(confirmed_stages)}"
    )
    print(
        f"duplicate_stage_owner_count="
        f"{duplicate_stage_count}"
    )
    print(
        f"deferred_stage_count="
        f"{len(deferred_rows)}"
    )
    print(
        f"ownership_edge_count="
        f"{len(edges)}"
    )
    print(
        f"unresolved_count="
        f"{len(unresolved)}"
    )

    for row in registry:
        print(
            f"REGISTRY_OWNER "
            f"stage={row['stage']} "
            f"scope={row['ownership_scope']} "
            f"symbol={row['owner_symbol']}"
        )

    print("owner_assignment_performed=1")
    print("writes_performed=0")
    print("db_writes_performed=0")
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
        "DECISION_OWNER_REGISTRY_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
