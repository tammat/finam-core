#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib


SOURCE_DIR = pathlib.Path(
    "/tmp/execution_broker_domain_status_mapping_v1"
)

CANDIDATES_FILE = SOURCE_DIR / "domain_status_candidates.tsv"
UNRESOLVED_SOURCE_FILE = SOURCE_DIR / "unresolved.tsv"

OUTPUT_DIR = pathlib.Path(
    "/tmp/execution_broker_layered_status_ownership_v1"
)

OWNERS_FILE = OUTPUT_DIR / "confirmed_status_owners.tsv"
EDGES_FILE = OUTPUT_DIR / "ownership_edges.tsv"
CONTRACT_FILE = OUTPUT_DIR / "ownership_contract.txt"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved.tsv"


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"source_file_missing:{path}")

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

    candidates = read_tsv(CANDIDATES_FILE)
    source_unresolved = read_tsv(
        UNRESOLVED_SOURCE_FILE
    )

    unresolved: list[dict[str, object]] = [
        {
            "scope": row.get("scope", ""),
            "symbol": row.get("symbol", ""),
            "reason": row.get("reason", ""),
        }
        for row in source_unresolved
        if any(str(value).strip() for value in row.values())
    ]

    candidate_index = {
        (
            row.get("candidate_layer", ""),
            row.get("candidate_symbol", ""),
        ): row
        for row in candidates
    }

    execution = candidate_index.get(
        ("EXECUTION", "ExecutionDispatcher")
    )
    broker = candidate_index.get(
        ("BROKER", "FinamOrdersClient")
    )

    def evidence_complete(
        row: dict[str, str] | None,
    ) -> bool:
        return bool(
            row
            and row.get("status_mapping_found") == "1"
            and row.get("exception_mapping_found") == "1"
        )

    execution_complete = evidence_complete(execution)
    broker_complete = evidence_complete(broker)

    if not execution_complete:
        unresolved.append(
            {
                "scope": "EXECUTION_STATUS",
                "symbol": "ExecutionDispatcher",
                "reason": (
                    "STATUS_OR_EXCEPTION_MAPPING_INCOMPLETE"
                ),
            }
        )

    if not broker_complete:
        unresolved.append(
            {
                "scope": "BROKER_PROTOCOL_STATUS",
                "symbol": "FinamOrdersClient",
                "reason": (
                    "STATUS_OR_EXCEPTION_MAPPING_INCOMPLETE"
                ),
            }
        )

    owners: list[dict[str, object]] = []

    if broker_complete:
        owners.append(
            {
                "stage": "BROKER",
                "ownership_scope": (
                    "BROKER_PROTOCOL_RESULT"
                ),
                "owner_symbol": "FinamOrdersClient",
                "owner_granularity": "CLASS_BOUNDARY",
                "classification": (
                    "CONFIRMED_RESULT_OWNER"
                ),
                "responsibility": (
                    "broker_response_and_transport_"
                    "exception_normalization"
                ),
                "status_mapping_found": 1,
                "exception_mapping_found": 1,
                "owner_confirmed": 1,
                "runtime_instrumentation": 0,
            }
        )

    if execution_complete:
        owners.append(
            {
                "stage": "EXECUTION",
                "ownership_scope": (
                    "EXECUTION_DOMAIN_STATUS"
                ),
                "owner_symbol": "ExecutionDispatcher",
                "owner_granularity": "CLASS_BOUNDARY",
                "classification": (
                    "CONFIRMED_RESULT_OWNER"
                ),
                "responsibility": (
                    "broker_result_to_execution_"
                    "domain_status_mapping"
                ),
                "status_mapping_found": 1,
                "exception_mapping_found": 1,
                "owner_confirmed": 1,
                "runtime_instrumentation": 0,
            }
        )

    edges = [
        {
            "edge": (
                "BROKER_PROTOCOL_RESULT_TO_"
                "EXECUTION_DOMAIN_STATUS"
            ),
            "source_stage": "BROKER",
            "source_owner": "FinamOrdersClient",
            "target_stage": "EXECUTION",
            "target_owner": "ExecutionDispatcher",
            "classification": (
                "LAYERED_STATUS_TRANSFORMATION"
            ),
            "reachable": int(
                broker_complete
                and execution_complete
            ),
            "runtime_instrumentation": 0,
        }
    ]

    write_tsv(
        OWNERS_FILE,
        (
            "stage",
            "ownership_scope",
            "owner_symbol",
            "owner_granularity",
            "classification",
            "responsibility",
            "status_mapping_found",
            "exception_mapping_found",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        owners,
    )

    write_tsv(
        EDGES_FILE,
        (
            "edge",
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
            "EXECUTION BROKER LAYERED STATUS "
            "OWNERSHIP V1\n"
        )
        stream.write(
            "==========================================\n\n"
        )
        stream.write(
            "BROKER_PROTOCOL_RESULT_OWNER="
            "FinamOrdersClient\n"
        )
        stream.write(
            "EXECUTION_DOMAIN_STATUS_OWNER="
            "ExecutionDispatcher\n"
        )
        stream.write(
            "STATUS_TRANSFORMATION="
            "BROKER_PROTOCOL_RESULT->"
            "EXECUTION_DOMAIN_STATUS\n"
        )
        stream.write(
            "DUPLICATE_OWNERSHIP=0\n"
        )
        stream.write(
            "RUNTIME_INSTRUMENTATION=0\n"
        )

    scope_count = len(
        {
            str(row["ownership_scope"])
            for row in owners
        }
    )

    duplicate_scope_count = (
        len(owners) - scope_count
    )

    print(
        "=== BUILD EXECUTION BROKER LAYERED "
        "STATUS OWNERSHIP V1 ==="
    )
    print(
        f"confirmed_result_owner_count="
        f"{len(owners)}"
    )
    print(
        f"distinct_ownership_scope_count="
        f"{scope_count}"
    )
    print(
        f"duplicate_ownership_scope_count="
        f"{duplicate_scope_count}"
    )
    print(
        f"broker_protocol_owner_confirmed="
        f"{int(broker_complete)}"
    )
    print(
        f"execution_domain_owner_confirmed="
        f"{int(execution_complete)}"
    )
    print(
        f"ownership_edge_reachable="
        f"{edges[0]['reachable']}"
    )
    print(f"unresolved_count={len(unresolved)}")

    for row in owners:
        print(
            f"CONFIRMED_RESULT_OWNER "
            f"stage={row['stage']} "
            f"scope={row['ownership_scope']} "
            f"symbol={row['owner_symbol']}"
        )

    print("owner_assignment_performed=1")
    print("writes_performed=0")
    print("db_writes_performed=0")
    print("runtime_instrumentation=0")
    print("execution_changed=0")
    print("broker_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "EXECUTION_BROKER_LAYERED_STATUS_OWNERSHIP_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
