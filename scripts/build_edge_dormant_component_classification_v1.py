#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib


SEMANTIC_DIR = pathlib.Path(
    "/tmp/edge_semantic_classification_v1"
)

DEPENDENCY_DIR = pathlib.Path(
    "/tmp/edge_candidate_dependency_injection_v3"
)

SANITY_DIR = pathlib.Path(
    "/tmp/edge_runtime_reachability_sanity_v1"
)

OUT = pathlib.Path(
    "/tmp/edge_dormant_component_classification_v1"
)

SEMANTIC_FILE = (
    SEMANTIC_DIR
    / "authoritative_decision_candidates.tsv"
)

DEPENDENCY_FILE = (
    DEPENDENCY_DIR
    / "candidate_summary.tsv"
)

SANITY_FILE = (
    SANITY_DIR
    / "candidate_summary.tsv"
)

DORMANT_FILE = (
    OUT
    / "dormant_edge_components.tsv"
)

DEFERRED_FILE = (
    OUT
    / "deferred_edge_stage.tsv"
)

EVIDENCE_FILE = (
    OUT
    / "evidence_matrix.tsv"
)

CONTRACT_FILE = (
    OUT
    / "edge_ownership_contract.txt"
)

UNRESOLVED_FILE = (
    OUT
    / "unresolved.tsv"
)

EXPECTED_IDENTITIES = {
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


def integer(
    row: dict[str, str],
    field: str,
) -> int:
    return int(
        row.get(field)
        or 0
    )


def main() -> int:
    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    semantic_rows = read_tsv(
        SEMANTIC_FILE
    )

    dependency_rows = read_tsv(
        DEPENDENCY_FILE
    )

    sanity_rows = read_tsv(
        SANITY_FILE
    )

    semantic_index = {
        (
            row["path"],
            row["qualified_name"],
        ): row
        for row in semantic_rows
        if (
            row.get(
                "semantic_classification"
            )
            == (
                "AUTHORITATIVE_EDGE_"
                "DECISION_CANDIDATE"
            )
        )
    }

    dependency_index = {
        row["candidate_symbol"]: row
        for row in dependency_rows
    }

    sanity_index = {
        row["candidate_symbol"]: row
        for row in sanity_rows
    }

    unresolved: list[
        dict[str, object]
    ] = []

    dormant_rows: list[
        dict[str, object]
    ] = []

    evidence_rows: list[
        dict[str, object]
    ] = []

    actual_identities = set(
        semantic_index
    )

    if (
        actual_identities
        != EXPECTED_IDENTITIES
    ):
        for path, symbol in sorted(
            EXPECTED_IDENTITIES
            - actual_identities
        ):
            unresolved.append(
                {
                    "scope": (
                        "SEMANTIC_IDENTITY"
                    ),
                    "candidate_symbol": (
                        symbol
                    ),
                    "reason": (
                        "EXPECTED_CANDIDATE_"
                        "MISSING"
                    ),
                }
            )

        for path, symbol in sorted(
            actual_identities
            - EXPECTED_IDENTITIES
        ):
            unresolved.append(
                {
                    "scope": (
                        "SEMANTIC_IDENTITY"
                    ),
                    "candidate_symbol": (
                        symbol
                    ),
                    "reason": (
                        "UNEXPECTED_CANDIDATE:"
                        f"{path}"
                    ),
                }
            )

    for (
        candidate_path,
        candidate_symbol,
    ) in sorted(
        EXPECTED_IDENTITIES
    ):
        semantic = semantic_index.get(
            (
                candidate_path,
                candidate_symbol,
            )
        )

        dependency = (
            dependency_index.get(
                candidate_symbol
            )
        )

        sanity = sanity_index.get(
            candidate_symbol
        )

        if semantic is None:
            continue

        if dependency is None:
            unresolved.append(
                {
                    "scope": (
                        "DEPENDENCY_EVIDENCE"
                    ),
                    "candidate_symbol": (
                        candidate_symbol
                    ),
                    "reason": (
                        "DEPENDENCY_SUMMARY_"
                        "MISSING"
                    ),
                }
            )
            continue

        if sanity is None:
            unresolved.append(
                {
                    "scope": (
                        "RUNTIME_SANITY"
                    ),
                    "candidate_symbol": (
                        candidate_symbol
                    ),
                    "reason": (
                        "SANITY_SUMMARY_"
                        "MISSING"
                    ),
                }
            )
            continue

        import_count = integer(
            dependency,
            "import_count",
        )

        parameter_count = integer(
            dependency,
            "parameter_binding_count",
        )

        annotation_count = integer(
            dependency,
            "annotation_binding_count",
        )

        factory_count = integer(
            dependency,
            "factory_return_count",
        )

        module_instance_count = integer(
            dependency,
            "module_instance_count",
        )

        assignment_count = integer(
            dependency,
            "dependency_assignment_count",
        )

        resolved_call_count = integer(
            dependency,
            "resolved_call_count",
        )

        registry_count = integer(
            sanity,
            "registry_reference_count",
        )

        dynamic_import_count = integer(
            sanity,
            "dynamic_import_count",
        )

        reflection_count = integer(
            sanity,
            "reflection_reference_count",
        )

        configuration_count = integer(
            sanity,
            "configuration_reference_count",
        )

        executable_reference_count = (
            integer(
                sanity,
                "executable_reference_count",
            )
        )

        dependency_evidence_count = (
            import_count
            + parameter_count
            + annotation_count
            + factory_count
            + module_instance_count
            + assignment_count
            + resolved_call_count
        )

        indirect_runtime_count = (
            registry_count
            + dynamic_import_count
            + reflection_count
            + configuration_count
        )

        dormant_evidence_complete = (
            dependency_evidence_count == 0
            and resolved_call_count == 0
            and indirect_runtime_count == 0
        )

        classification = (
            "DORMANT_EDGE_DECISION_COMPONENT"
            if dormant_evidence_complete
            else "UNRESOLVED_EDGE_COMPONENT"
        )

        reason = (
            "NO_CONSTRUCTION_DI_FACTORY_"
            "RESOLVED_CALL_OR_INDIRECT_RUNTIME_BINDING"
            if dormant_evidence_complete
            else "RUNTIME_OR_DEPENDENCY_EVIDENCE_PRESENT"
        )

        evidence_rows.append(
            {
                "candidate_path": (
                    candidate_path
                ),
                "candidate_symbol": (
                    candidate_symbol
                ),
                "import_count": (
                    import_count
                ),
                "parameter_binding_count": (
                    parameter_count
                ),
                "annotation_binding_count": (
                    annotation_count
                ),
                "factory_return_count": (
                    factory_count
                ),
                "module_instance_count": (
                    module_instance_count
                ),
                "dependency_assignment_count": (
                    assignment_count
                ),
                "resolved_call_count": (
                    resolved_call_count
                ),
                "registry_reference_count": (
                    registry_count
                ),
                "dynamic_import_count": (
                    dynamic_import_count
                ),
                "reflection_reference_count": (
                    reflection_count
                ),
                "configuration_reference_count": (
                    configuration_count
                ),
                "sanity_executable_reference_count": (
                    executable_reference_count
                ),
                "dormant_evidence_complete": int(
                    dormant_evidence_complete
                ),
            }
        )

        if dormant_evidence_complete:
            dormant_rows.append(
                {
                    "stage": "EDGE",
                    "ownership_scope": (
                        "EDGE_DECISION"
                    ),
                    "candidate_path": (
                        candidate_path
                    ),
                    "candidate_symbol": (
                        candidate_symbol
                    ),
                    "semantic_classification": (
                        semantic[
                            "semantic_classification"
                        ]
                    ),
                    "classification": (
                        classification
                    ),
                    "reason": reason,
                    "owner_confirmed": 0,
                    "runtime_instrumentation": 0,
                }
            )
        else:
            unresolved.append(
                {
                    "scope": (
                        "DORMANT_CLASSIFICATION"
                    ),
                    "candidate_symbol": (
                        candidate_symbol
                    ),
                    "reason": reason,
                }
            )

    deferred_rows: list[
        dict[str, object]
    ] = []

    if (
        len(dormant_rows) == 3
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
                "dormant_component_count": (
                    len(dormant_rows)
                ),
                "candidate_symbols": (
                    ",".join(
                        sorted(
                            str(
                                row[
                                    "candidate_symbol"
                                ]
                            )
                            for row
                            in dormant_rows
                        )
                    )
                ),
                "reason": (
                    "NO_EXECUTABLE_EDGE_"
                    "DECISION_OWNER_PROVEN"
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    dormant_fields = (
        "stage",
        "ownership_scope",
        "candidate_path",
        "candidate_symbol",
        "semantic_classification",
        "classification",
        "reason",
        "owner_confirmed",
        "runtime_instrumentation",
    )

    evidence_fields = (
        "candidate_path",
        "candidate_symbol",
        "import_count",
        "parameter_binding_count",
        "annotation_binding_count",
        "factory_return_count",
        "module_instance_count",
        "dependency_assignment_count",
        "resolved_call_count",
        "registry_reference_count",
        "dynamic_import_count",
        "reflection_reference_count",
        "configuration_reference_count",
        "sanity_executable_reference_count",
        "dormant_evidence_complete",
    )

    write_tsv(
        DORMANT_FILE,
        dormant_fields,
        dormant_rows,
    )

    write_tsv(
        DEFERRED_FILE,
        (
            "stage",
            "ownership_scope",
            "status",
            "confirmed_owner_count",
            "dormant_component_count",
            "candidate_symbols",
            "reason",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        deferred_rows,
    )

    write_tsv(
        EVIDENCE_FILE,
        evidence_fields,
        evidence_rows,
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

    confirmed_owner_count = 0
    dormant_count = len(
        dormant_rows
    )
    deferred_count = len(
        deferred_rows
    )

    with CONTRACT_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "EDGE OWNERSHIP CONTRACT V1\n"
        )
        stream.write(
            "==========================\n\n"
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
            f"{dormant_count}\n"
        )
        stream.write(
            f"DEFERRED_EDGE_STAGE_COUNT="
            f"{deferred_count}\n"
        )
        stream.write(
            f"UNRESOLVED_COUNT="
            f"{len(unresolved)}\n"
        )
        stream.write(
            "RUNTIME_INSTRUMENTATION=0\n"
        )
        stream.write(
            "MICRO_LIVE_ALLOWED=0\n"
        )

    print(
        "=== BUILD EDGE DORMANT "
        "COMPONENT CLASSIFICATION V1 ==="
    )
    print(
        "confirmed_edge_owner_count=0"
    )
    print(
        f"dormant_edge_component_count="
        f"{dormant_count}"
    )
    print(
        f"deferred_edge_stage_count="
        f"{deferred_count}"
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
            f"path="
            f"{row['candidate_path']} "
            f"class="
            f"{row['classification']}"
        )

    print(
        "edge_stage_status=DEFERRED"
    )
    print("edge_owner=DEFERRED")
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
        "EDGE_DORMANT_COMPONENT_"
        "CLASSIFICATION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
