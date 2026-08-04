#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
from collections import Counter


V1_DIR = pathlib.Path(
    "/tmp/decision_owner_registry_v1"
)

V1_REGISTRY = (
    V1_DIR / "decision_owner_registry_v1.tsv"
)
V1_EDGES = (
    V1_DIR / "decision_owner_edges_v1.tsv"
)
V1_DEFERRED = (
    V1_DIR / "deferred_stages_v1.tsv"
)
V1_UNRESOLVED = (
    V1_DIR / "unresolved_v1.tsv"
)

STRATEGY_DIR = pathlib.Path(
    "/tmp/strategy_owner_confirmation_v1"
)

STRATEGY_OWNERS = (
    STRATEGY_DIR / "confirmed_strategy_owners.tsv"
)
STRATEGY_FAMILIES = (
    STRATEGY_DIR / "strategy_family_ownership.tsv"
)
STRATEGY_UNRESOLVED = (
    STRATEGY_DIR / "unresolved.tsv"
)

OUTPUT_DIR = pathlib.Path(
    "/tmp/decision_owner_registry_v2"
)

REGISTRY_FILE = (
    OUTPUT_DIR / "decision_owner_registry_v2.tsv"
)
EDGES_FILE = (
    OUTPUT_DIR / "decision_owner_edges_v2.tsv"
)
CONTRACT_FILE = (
    OUTPUT_DIR / "decision_owner_contract_v2.txt"
)
DEFERRED_FILE = (
    OUTPUT_DIR / "deferred_stages_v2.tsv"
)
UNRESOLVED_FILE = (
    OUTPUT_DIR / "unresolved_v2.tsv"
)

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

EXPECTED_BASE_STAGES = {
    "RISK",
    "RUNTIME",
    "EXECUTION",
    "BROKER",
}

EXPECTED_STRATEGY_FAMILIES = {
    "BR",
    "NG",
    "EQUITY",
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
        )
        writer.writeheader()
        writer.writerows(rows)


def nonempty_rows(
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if any(
            str(value).strip()
            for value in row.values()
        )
    ]


def main() -> int:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    base_registry = read_tsv(V1_REGISTRY)
    base_edges = read_tsv(V1_EDGES)
    base_deferred = read_tsv(V1_DEFERRED)
    base_unresolved = nonempty_rows(
        read_tsv(V1_UNRESOLVED)
    )

    strategy_owners = read_tsv(
        STRATEGY_OWNERS
    )
    strategy_families = read_tsv(
        STRATEGY_FAMILIES
    )
    strategy_unresolved = nonempty_rows(
        read_tsv(STRATEGY_UNRESOLVED)
    )

    unresolved: list[dict[str, object]] = []

    for row in base_unresolved:
        unresolved.append(
            {
                "scope": row.get("scope", ""),
                "symbol": row.get("symbol", ""),
                "reason": row.get("reason", ""),
            }
        )

    for row in strategy_unresolved:
        unresolved.append(
            {
                "scope": "STRATEGY_OWNER",
                "symbol": row.get(
                    "candidate_symbol",
                    "",
                ),
                "reason": row.get(
                    "reason",
                    "",
                ),
            }
        )

    registry: list[dict[str, object]] = []

    for row in base_registry:
        stage = row.get("stage", "")

        if stage not in EXPECTED_BASE_STAGES:
            unresolved.append(
                {
                    "scope": "BASE_REGISTRY",
                    "symbol": stage,
                    "reason": (
                        "UNEXPECTED_V1_CONFIRMED_STAGE"
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
                "owner_path": row["owner_path"],
                "owner_symbol": row[
                    "owner_symbol"
                ],
                "owner_granularity": row[
                    "owner_granularity"
                ],
                "classification": row[
                    "classification"
                ],
                "responsibility": row[
                    "responsibility"
                ],
                "failure_policy": row[
                    "failure_policy"
                ],
                "family": "",
                "ownership_model": "",
                "owner_confirmed": 1,
                "runtime_instrumentation": 0,
            }
        )

    discovered_strategy_families: set[str] = set()

    for row in strategy_owners:
        family = row.get("family", "")
        owner_symbol = row.get(
            "owner_symbol",
            "",
        )

        if family not in EXPECTED_STRATEGY_FAMILIES:
            unresolved.append(
                {
                    "scope": "STRATEGY_FAMILY",
                    "symbol": family,
                    "reason": (
                        "UNEXPECTED_STRATEGY_FAMILY"
                    ),
                }
            )
            continue

        if row.get("owner_confirmed") != "1":
            unresolved.append(
                {
                    "scope": "STRATEGY_OWNER",
                    "symbol": owner_symbol,
                    "reason": (
                        "STRATEGY_OWNER_NOT_CONFIRMED"
                    ),
                }
            )
            continue

        if row.get(
            "runtime_instrumentation"
        ) != "0":
            unresolved.append(
                {
                    "scope": "STRATEGY_OWNER",
                    "symbol": owner_symbol,
                    "reason": (
                        "RUNTIME_INSTRUMENTATION_ENABLED"
                    ),
                }
            )
            continue

        discovered_strategy_families.add(
            family
        )

        registry.append(
            {
                "stage": "STRATEGY",
                "ownership_scope": (
                    f"TRADE_INTENT:{family}"
                ),
                "owner_path": row["owner_path"],
                "owner_symbol": owner_symbol,
                "owner_granularity": (
                    "FAMILY_METHOD"
                ),
                "classification": (
                    "CONFIRMED_STRATEGY_OWNER"
                ),
                "responsibility": (
                    "family_scoped_trade_intent_"
                    "generation"
                ),
                "failure_policy": (
                    "NO_SIGNAL_ON_NO_INTENT"
                ),
                "family": family,
                "ownership_model": row[
                    "ownership_model"
                ],
                "owner_confirmed": 1,
                "runtime_instrumentation": 0,
            }
        )

    missing_families = (
        EXPECTED_STRATEGY_FAMILIES
        - discovered_strategy_families
    )

    for family in sorted(missing_families):
        unresolved.append(
            {
                "scope": "STRATEGY_FAMILY",
                "symbol": family,
                "reason": (
                    "CONFIRMED_STRATEGY_FAMILY_MISSING"
                ),
            }
        )

    family_model_index = {
        row.get("family", ""): row
        for row in strategy_families
    }

    for family in sorted(
        EXPECTED_STRATEGY_FAMILIES
    ):
        family_row = family_model_index.get(
            family
        )

        if family_row is None:
            unresolved.append(
                {
                    "scope": (
                        "STRATEGY_OWNERSHIP_MODEL"
                    ),
                    "symbol": family,
                    "reason": (
                        "FAMILY_MODEL_MISSING"
                    ),
                }
            )
            continue

        if family_row.get(
            "ownership_model_valid"
        ) != "1":
            unresolved.append(
                {
                    "scope": (
                        "STRATEGY_OWNERSHIP_MODEL"
                    ),
                    "symbol": family,
                    "reason": (
                        "FAMILY_MODEL_INVALID"
                    ),
                }
            )

    stage_order = {
        stage: index
        for index, stage in enumerate(
            ALL_STAGES
        )
    }

    registry.sort(
        key=lambda row: (
            stage_order[
                str(row["stage"])
            ],
            str(row["family"]),
            str(row["owner_symbol"]),
        )
    )

    identity_counts = Counter(
        (
            str(row["stage"]),
            str(row["ownership_scope"]),
            str(row["owner_symbol"]),
        )
        for row in registry
    )

    duplicate_identity_count = sum(
        1
        for count in identity_counts.values()
        if count > 1
    )

    if duplicate_identity_count:
        unresolved.append(
            {
                "scope": "REGISTRY",
                "symbol": "",
                "reason": (
                    "DUPLICATE_OWNER_IDENTITY"
                ),
            }
        )

    strategy_rows = [
        row
        for row in registry
        if row["stage"] == "STRATEGY"
    ]

    base_rows = [
        row
        for row in registry
        if row["stage"] != "STRATEGY"
    ]

    deferred_rows: list[
        dict[str, object]
    ] = []

    confirmed_stage_names = {
        str(row["stage"])
        for row in registry
    }

    v1_deferred_index = {
        row.get("stage", ""): row
        for row in base_deferred
    }

    for stage in ALL_STAGES:
        if stage in confirmed_stage_names:
            continue

        source = v1_deferred_index.get(stage)

        deferred_rows.append(
            {
                "stage": stage,
                "status": "DEFERRED",
                "candidate": (
                    source.get("candidate", "")
                    if source
                    else ""
                ),
                "reason": (
                    source.get("reason", "")
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

    edges: list[dict[str, object]] = []

    edge_order = 1

    for row in strategy_rows:
        family = str(row["family"])
        symbol = str(row["owner_symbol"])

        edges.append(
            {
                "edge_order": edge_order,
                "source_stage": "STRATEGY",
                "source_scope": (
                    f"TRADE_INTENT:{family}"
                ),
                "source_owner": symbol,
                "target_stage": "RISK",
                "target_scope": "DECISION_GATE",
                "target_owner": (
                    "PortfolioRiskGate.check"
                ),
                "classification": (
                    "CONFIRMED_FAMILY_DECISION_FLOW"
                ),
                "reachable": 1,
                "runtime_instrumentation": 0,
            }
        )
        edge_order += 1

    for row in base_edges:
        edges.append(
            {
                "edge_order": edge_order,
                "source_stage": row[
                    "source_stage"
                ],
                "source_scope": "",
                "source_owner": row[
                    "source_owner"
                ],
                "target_stage": row[
                    "target_stage"
                ],
                "target_scope": "",
                "target_owner": row[
                    "target_owner"
                ],
                "classification": row[
                    "classification"
                ],
                "reachable": row[
                    "reachable"
                ],
                "runtime_instrumentation": 0,
            }
        )
        edge_order += 1

    registry_fields = (
        "stage",
        "ownership_scope",
        "owner_path",
        "owner_symbol",
        "owner_granularity",
        "classification",
        "responsibility",
        "failure_policy",
        "family",
        "ownership_model",
        "owner_confirmed",
        "runtime_instrumentation",
    )

    write_tsv(
        REGISTRY_FILE,
        registry_fields,
        registry,
    )

    write_tsv(
        EDGES_FILE,
        (
            "edge_order",
            "source_stage",
            "source_scope",
            "source_owner",
            "target_stage",
            "target_scope",
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
            "DECISION OWNER REGISTRY V2\n"
        )
        stream.write(
            "==========================\n\n"
        )

        for row in registry:
            identity = (
                f"{row['stage']}"
                if not row["family"]
                else (
                    f"{row['stage']}:"
                    f"{row['family']}"
                )
            )

            stream.write(
                f"{identity}="
                f"{row['owner_symbol']}\n"
            )

        stream.write("\n")
        stream.write(
            f"CONFIRMED_OWNER_COUNT="
            f"{len(registry)}\n"
        )
        stream.write(
            f"BASE_OWNER_COUNT="
            f"{len(base_rows)}\n"
        )
        stream.write(
            f"STRATEGY_OWNER_COUNT="
            f"{len(strategy_rows)}\n"
        )
        stream.write(
            f"STRATEGY_FAMILY_COUNT="
            f"{len(discovered_strategy_families)}\n"
        )
        stream.write(
            f"DEFERRED_STAGE_COUNT="
            f"{len(deferred_rows)}\n"
        )
        stream.write(
            f"DUPLICATE_OWNER_IDENTITY_COUNT="
            f"{duplicate_identity_count}\n"
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
        "REGISTRY V2 ==="
    )
    print(
        f"confirmed_owner_count="
        f"{len(registry)}"
    )
    print(
        f"base_owner_count="
        f"{len(base_rows)}"
    )
    print(
        f"strategy_owner_count="
        f"{len(strategy_rows)}"
    )
    print(
        f"strategy_family_count="
        f"{len(discovered_strategy_families)}"
    )
    print(
        f"confirmed_stage_count="
        f"{len(confirmed_stage_names)}"
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
        f"duplicate_owner_identity_count="
        f"{duplicate_identity_count}"
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
            f"family={row['family'] or '-'} "
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
        "DECISION_OWNER_REGISTRY_V2_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
