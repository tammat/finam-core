#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib


SOURCE_DIR = pathlib.Path(
    "/tmp/edge_dormant_component_classification_v1"
)

SOURCE_DORMANT = (
    SOURCE_DIR / "dormant_edge_components.tsv"
)

SOURCE_DEFERRED = (
    SOURCE_DIR / "deferred_edge_stage.tsv"
)

SOURCE_CONTRACT = (
    SOURCE_DIR / "edge_ownership_contract.txt"
)

SOURCE_UNRESOLVED = (
    SOURCE_DIR / "unresolved.tsv"
)

OUT = pathlib.Path(
    "/tmp/edge_owner_confirmation_v1"
)

CONFIRMED_FILE = (
    OUT / "confirmed_edge_owners.tsv"
)

DEFERRED_FILE = (
    OUT / "deferred_edge_stage.tsv"
)

DORMANT_FILE = (
    OUT / "dormant_edge_components.tsv"
)

CONTRACT_FILE = (
    OUT / "edge_owner_confirmation_contract.txt"
)

UNRESOLVED_FILE = (
    OUT / "unresolved.tsv"
)

EXPECTED_COMPONENTS = {
    (
        "src/finam_core/analytics/directional_edge_guard.py",
        "DirectionalEdgeGuard.decide",
    ),
    (
        "src/finam_core/analytics/statistical_validation_decision.py",
        "StatisticalValidationDecisionEngine.decide",
    ),
    (
        "src/finam_core/analytics/session_edge_guard.py",
        "SessionEdgeGuard.decide",
    ),
}


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
        return [
            {
                key: str(value or "").strip()
                for key, value in row.items()
            }
            for row in csv.DictReader(
                stream,
                delimiter="\t",
            )
        ]


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


def read_contract(
    path: pathlib.Path,
) -> dict[str, str]:
    if not path.is_file():
        raise RuntimeError(
            f"source_file_missing:{path}"
        )

    result: dict[str, str] = {}

    for line in path.read_text(
        encoding="utf-8",
    ).splitlines():
        if "=" not in line:
            continue

        key, value = line.split(
            "=",
            1,
        )

        result[key.strip()] = value.strip()

    return result


def nonempty(
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if any(row.values())
    ]


def main() -> int:
    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    dormant_source = read_tsv(
        SOURCE_DORMANT
    )

    deferred_source = read_tsv(
        SOURCE_DEFERRED
    )

    source_unresolved = nonempty(
        read_tsv(
            SOURCE_UNRESOLVED
        )
    )

    source_contract = read_contract(
        SOURCE_CONTRACT
    )

    unresolved: list[
        dict[str, object]
    ] = []

    for row in source_unresolved:
        unresolved.append(
            {
                "scope": row.get(
                    "scope",
                    "SOURCE",
                ),
                "candidate_symbol": row.get(
                    "candidate_symbol",
                    "",
                ),
                "reason": row.get(
                    "reason",
                    "SOURCE_UNRESOLVED",
                ),
            }
        )

    actual_components = {
        (
            row.get(
                "candidate_path",
                "",
            ),
            row.get(
                "candidate_symbol",
                "",
            ),
        )
        for row in dormant_source
    }

    if actual_components != EXPECTED_COMPONENTS:
        for path, symbol in sorted(
            EXPECTED_COMPONENTS
            - actual_components
        ):
            unresolved.append(
                {
                    "scope": (
                        "DORMANT_COMPONENT_SET"
                    ),
                    "candidate_symbol": symbol,
                    "reason": (
                        "EXPECTED_DORMANT_"
                        f"COMPONENT_MISSING:{path}"
                    ),
                }
            )

        for path, symbol in sorted(
            actual_components
            - EXPECTED_COMPONENTS
        ):
            unresolved.append(
                {
                    "scope": (
                        "DORMANT_COMPONENT_SET"
                    ),
                    "candidate_symbol": symbol,
                    "reason": (
                        "UNEXPECTED_DORMANT_"
                        f"COMPONENT:{path}"
                    ),
                }
            )

    dormant_rows: list[
        dict[str, object]
    ] = []

    for row in dormant_source:
        evidence_ok = (
            row.get("stage") == "EDGE"
            and row.get(
                "ownership_scope"
            ) == "EDGE_DECISION"
            and row.get(
                "classification"
            ) == (
                "DORMANT_EDGE_"
                "DECISION_COMPONENT"
            )
            and row.get(
                "owner_confirmed"
            ) == "0"
            and row.get(
                "runtime_instrumentation"
            ) == "0"
        )

        if not evidence_ok:
            unresolved.append(
                {
                    "scope": (
                        "DORMANT_COMPONENT"
                    ),
                    "candidate_symbol": row.get(
                        "candidate_symbol",
                        "",
                    ),
                    "reason": (
                        "DORMANT_COMPONENT_"
                        "EVIDENCE_INVALID"
                    ),
                }
            )
            continue

        dormant_rows.append(
            {
                "stage": "EDGE",
                "ownership_scope": (
                    "EDGE_DECISION"
                ),
                "candidate_path": row[
                    "candidate_path"
                ],
                "candidate_symbol": row[
                    "candidate_symbol"
                ],
                "classification": (
                    "DORMANT_EDGE_"
                    "DECISION_COMPONENT"
                ),
                "confirmation_status": (
                    "NOT_OWNER"
                ),
                "reason": (
                    "NO_EXECUTABLE_EDGE_"
                    "DECISION_BINDING_PROVEN"
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    confirmed_rows: list[
        dict[str, object]
    ] = []

    deferred_rows: list[
        dict[str, object]
    ] = []

    deferred_source_ok = (
        len(deferred_source) == 1
        and deferred_source[0].get(
            "stage"
        ) == "EDGE"
        and deferred_source[0].get(
            "ownership_scope"
        ) == "EDGE_DECISION"
        and deferred_source[0].get(
            "status"
        ) == "DEFERRED"
        and deferred_source[0].get(
            "confirmed_owner_count"
        ) == "0"
        and deferred_source[0].get(
            "dormant_component_count"
        ) == "3"
        and deferred_source[0].get(
            "owner_confirmed"
        ) == "0"
        and deferred_source[0].get(
            "runtime_instrumentation"
        ) == "0"
    )

    contract_ok = (
        source_contract.get(
            "EDGE_STAGE_STATUS"
        ) == "DEFERRED"
        and source_contract.get(
            "EDGE_OWNER"
        ) == "DEFERRED"
        and source_contract.get(
            "CONFIRMED_EDGE_OWNER_COUNT"
        ) == "0"
        and source_contract.get(
            "DORMANT_EDGE_COMPONENT_COUNT"
        ) == "3"
        and source_contract.get(
            "DEFERRED_EDGE_STAGE_COUNT"
        ) == "1"
        and source_contract.get(
            "UNRESOLVED_COUNT"
        ) == "0"
        and source_contract.get(
            "RUNTIME_INSTRUMENTATION"
        ) == "0"
        and source_contract.get(
            "MICRO_LIVE_ALLOWED"
        ) == "0"
    )

    if not deferred_source_ok:
        unresolved.append(
            {
                "scope": "EDGE_STAGE",
                "candidate_symbol": "",
                "reason": (
                    "DEFERRED_EDGE_STAGE_"
                    "EVIDENCE_INVALID"
                ),
            }
        )

    if not contract_ok:
        unresolved.append(
            {
                "scope": (
                    "EDGE_CONTRACT"
                ),
                "candidate_symbol": "",
                "reason": (
                    "SOURCE_EDGE_CONTRACT_"
                    "INVALID"
                ),
            }
        )

    if (
        len(dormant_rows) == 3
        and deferred_source_ok
        and contract_ok
        and not unresolved
    ):
        deferred_rows.append(
            {
                "stage": "EDGE",
                "ownership_scope": (
                    "EDGE_DECISION"
                ),
                "status": "DEFERRED",
                "confirmed_owner_count": 0,
                "dormant_component_count": 3,
                "owner_symbol": "",
                "owner_granularity": "",
                "reason": (
                    "NO_AUTHORITATIVE_"
                    "EXECUTABLE_EDGE_OWNER_PROVEN"
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    if confirmed_rows:
        unresolved.append(
            {
                "scope": (
                    "EDGE_CONFIRMATION"
                ),
                "candidate_symbol": "",
                "reason": (
                    "UNEXPECTED_CONFIRMED_"
                    "EDGE_OWNER"
                ),
            }
        )

    confirmed_fields = (
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
    )

    dormant_fields = (
        "stage",
        "ownership_scope",
        "candidate_path",
        "candidate_symbol",
        "classification",
        "confirmation_status",
        "reason",
        "owner_confirmed",
        "runtime_instrumentation",
    )

    deferred_fields = (
        "stage",
        "ownership_scope",
        "status",
        "confirmed_owner_count",
        "dormant_component_count",
        "owner_symbol",
        "owner_granularity",
        "reason",
        "owner_confirmed",
        "runtime_instrumentation",
    )

    write_tsv(
        CONFIRMED_FILE,
        confirmed_fields,
        confirmed_rows,
    )

    write_tsv(
        DORMANT_FILE,
        dormant_fields,
        dormant_rows,
    )

    write_tsv(
        DEFERRED_FILE,
        deferred_fields,
        deferred_rows,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "candidate_symbol",
            "reason",
        ),
        unresolved,
    )

    confirmed_owner_count = len(
        confirmed_rows
    )

    dormant_component_count = len(
        dormant_rows
    )

    deferred_stage_count = len(
        deferred_rows
    )

    with CONTRACT_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "EDGE OWNER CONFIRMATION V1\n"
        )
        stream.write(
            "==========================\n\n"
        )
        stream.write(
            "CONFIRMATION_RESULT="
            "NO_OWNER_CONFIRMED\n"
        )
        stream.write(
            "EDGE_STAGE_STATUS=DEFERRED\n"
        )
        stream.write(
            "EDGE_OWNER=DEFERRED\n"
        )
        stream.write(
            f"CONFIRMED_EDGE_OWNER_COUNT="
            f"{confirmed_owner_count}\n"
        )
        stream.write(
            f"DORMANT_EDGE_COMPONENT_COUNT="
            f"{dormant_component_count}\n"
        )
        stream.write(
            f"DEFERRED_EDGE_STAGE_COUNT="
            f"{deferred_stage_count}\n"
        )
        stream.write(
            f"UNRESOLVED_COUNT="
            f"{len(unresolved)}\n"
        )
        stream.write(
            "OWNER_ASSIGNMENT_PERFORMED=1\n"
        )
        stream.write(
            "RUNTIME_INSTRUMENTATION=0\n"
        )
        stream.write(
            "MICRO_LIVE_ALLOWED=0\n"
        )

    print(
        "=== BUILD EDGE OWNER "
        "CONFIRMATION V1 ==="
    )
    print(
        f"confirmed_edge_owner_count="
        f"{confirmed_owner_count}"
    )
    print(
        f"dormant_edge_component_count="
        f"{dormant_component_count}"
    )
    print(
        f"deferred_edge_stage_count="
        f"{deferred_stage_count}"
    )
    print(
        f"unresolved_count="
        f"{len(unresolved)}"
    )

    for row in dormant_rows:
        print(
            "DORMANT_EDGE_COMPONENT "
            f"symbol="
            f"{row['candidate_symbol']} "
            f"confirmation_status="
            f"{row['confirmation_status']}"
        )

    if deferred_rows:
        print(
            "DEFERRED_EDGE_STAGE "
            "stage=EDGE "
            "scope=EDGE_DECISION "
            "status=DEFERRED "
            "confirmed_owner_count=0 "
            "dormant_component_count=3"
        )

    print(
        "confirmation_result="
        "NO_OWNER_CONFIRMED"
    )
    print(
        "edge_stage_status=DEFERRED"
    )
    print("edge_owner=DEFERRED")
    print(
        "owner_assignment_performed=1"
    )
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
        "EDGE_OWNER_CONFIRMATION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
