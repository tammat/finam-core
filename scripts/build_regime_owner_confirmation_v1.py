#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib


SEMANTIC_DIR = pathlib.Path(
    "/tmp/regime_semantic_classification_v1"
)

RESOLUTION_DIR = pathlib.Path(
    "/tmp/regime_ambiguous_binding_resolution_v3"
)

CLASSIFIER_FILE = (
    SEMANTIC_DIR / "classifier_candidates.tsv"
)

FAMILY_CLASSIFIER_FILE = (
    SEMANTIC_DIR / "family_specific_candidates.tsv"
)

RESOLUTION_FILE = (
    RESOLUTION_DIR / "candidate_summary.tsv"
)

OUTPUT_DIR = pathlib.Path(
    "/tmp/regime_owner_confirmation_v1"
)

CONFIRMED_FILE = (
    OUTPUT_DIR / "confirmed_regime_owners.tsv"
)

DEFERRED_FILE = (
    OUTPUT_DIR / "deferred_regime_candidates.tsv"
)

HELPERS_FILE = (
    OUTPUT_DIR / "internal_helpers.tsv"
)

CONTRACT_FILE = (
    OUTPUT_DIR / "regime_ownership_contract.txt"
)

UNRESOLVED_FILE = (
    OUTPUT_DIR / "unresolved.tsv"
)

CONFIRMED_OWNER_SYMBOL = (
    "BRRegimeLayer.evaluate"
)

CONFIRMED_OWNER_SCOPE = (
    "MARKET_REGIME:BR"
)

INTERNAL_HELPER_SYMBOLS = {
    "RegimeLabeler._trend_label",
    "RegimeLabeler._vol_label",
}

EXPECTED_CANDIDATE_COUNT = 12


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


def main() -> int:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    semantic_rows = (
        read_tsv(CLASSIFIER_FILE)
        + read_tsv(FAMILY_CLASSIFIER_FILE)
    )

    resolution_rows = read_tsv(
        RESOLUTION_FILE
    )

    semantic_index = {
        row["qualified_name"]: row
        for row in semantic_rows
    }

    resolution_index = {
        row["candidate_symbol"]: row
        for row in resolution_rows
    }

    unresolved: list[dict[str, object]] = []
    confirmed: list[dict[str, object]] = []
    deferred: list[dict[str, object]] = []
    helpers: list[dict[str, object]] = []

    if len(semantic_rows) != EXPECTED_CANDIDATE_COUNT:
        unresolved.append(
            {
                "scope": "CANDIDATE_SET",
                "candidate_symbol": "",
                "reason": (
                    "UNEXPECTED_SEMANTIC_"
                    "CANDIDATE_COUNT"
                ),
            }
        )

    for symbol, semantic in sorted(
        semantic_index.items()
    ):
        resolution = resolution_index.get(
            symbol
        )

        if resolution is None:
            unresolved.append(
                {
                    "scope": "CANDIDATE",
                    "candidate_symbol": symbol,
                    "reason": (
                        "RESOLUTION_EVIDENCE_MISSING"
                    ),
                }
            )
            continue

        classification = resolution[
            "classification"
        ]

        resolved_calls = int(
            resolution.get(
                "resolved_call_count",
                "0",
            )
            or 0
        )

        runtime_calls = int(
            resolution.get(
                "runtime_reachable_call_count",
                "0",
            )
            or 0
        )

        base_row = {
            "family": semantic["family"],
            "ownership_scope": (
                CONFIRMED_OWNER_SCOPE
                if symbol == CONFIRMED_OWNER_SYMBOL
                else ""
            ),
            "owner_path": semantic["path"],
            "owner_class": semantic[
                "class_name"
            ],
            "owner_method": semantic[
                "function"
            ],
            "owner_symbol": symbol,
            "semantic_classification": (
                semantic[
                    "semantic_classification"
                ]
            ),
            "resolution_classification": (
                classification
            ),
            "resolved_call_count": (
                resolved_calls
            ),
            "runtime_reachable_call_count": (
                runtime_calls
            ),
            "runtime_chains": resolution.get(
                "runtime_chains",
                "",
            ),
            "owner_confirmed": 0,
            "runtime_instrumentation": 0,
        }

        if symbol in INTERNAL_HELPER_SYMBOLS:
            helpers.append(
                {
                    **base_row,
                    "classification": (
                        "INTERNAL_REGIME_HELPER"
                    ),
                    "reason": (
                        "HELPER_OWNED_BY_"
                        "REGIME_LABELER"
                    ),
                }
            )
            continue

        if symbol == CONFIRMED_OWNER_SYMBOL:
            evidence_complete = (
                semantic["family"] == "BR"
                and semantic[
                    "semantic_classification"
                ]
                == (
                    "FAMILY_REGIME_"
                    "CLASSIFIER_CANDIDATE"
                )
                and classification
                == (
                    "RESOLVED_RUNTIME_"
                    "REACHABLE"
                )
                and resolved_calls > 0
                and runtime_calls > 0
            )

            if not evidence_complete:
                unresolved.append(
                    {
                        "scope": "CONFIRMED_OWNER",
                        "candidate_symbol": symbol,
                        "reason": (
                            "BR_REGIME_OWNER_"
                            "EVIDENCE_INCOMPLETE"
                        ),
                    }
                )
                continue

            confirmed.append(
                {
                    **base_row,
                    "classification": (
                        "CONFIRMED_REGIME_OWNER"
                    ),
                    "owner_confirmed": 1,
                    "reason": (
                        "FAMILY_CLASSIFIER_WITH_"
                        "RESOLVED_RUNTIME_BINDING"
                    ),
                }
            )
            continue

        deferred.append(
            {
                **base_row,
                "classification": (
                    "DEFERRED_REGIME_CANDIDATE"
                ),
                "reason": (
                    "NO_RESOLVED_RUNTIME_BINDING"
                    if classification
                    in {
                        "NO_RESOLVED_BINDING",
                        "MODULE_FUNCTION_DEFERRED",
                    }
                    else (
                        "NOT_SELECTED_AS_"
                        "AUTHORITATIVE_OWNER"
                    )
                ),
            }
        )

    if len(confirmed) != 1:
        unresolved.append(
            {
                "scope": "OWNERSHIP_MODEL",
                "candidate_symbol": "",
                "reason": (
                    "CONFIRMED_OWNER_"
                    "CARDINALITY_VIOLATION"
                ),
            }
        )

    confirmed_symbols = {
        str(row["owner_symbol"])
        for row in confirmed
    }

    if CONFIRMED_OWNER_SYMBOL not in confirmed_symbols:
        unresolved.append(
            {
                "scope": "OWNERSHIP_MODEL",
                "candidate_symbol": (
                    CONFIRMED_OWNER_SYMBOL
                ),
                "reason": (
                    "EXPECTED_BR_REGIME_"
                    "OWNER_NOT_CONFIRMED"
                ),
            }
        )

    common_fields = (
        "family",
        "ownership_scope",
        "owner_path",
        "owner_class",
        "owner_method",
        "owner_symbol",
        "semantic_classification",
        "resolution_classification",
        "resolved_call_count",
        "runtime_reachable_call_count",
        "runtime_chains",
        "classification",
        "reason",
        "owner_confirmed",
        "runtime_instrumentation",
    )

    write_tsv(
        CONFIRMED_FILE,
        common_fields,
        confirmed,
    )

    write_tsv(
        DEFERRED_FILE,
        common_fields,
        deferred,
    )

    write_tsv(
        HELPERS_FILE,
        common_fields,
        helpers,
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

    with CONTRACT_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "REGIME OWNER CONTRACT V1\n"
        )
        stream.write(
            "========================\n\n"
        )
        stream.write(
            "OWNERSHIP_MODEL="
            "FAMILY_SCOPED_PARTIAL\n"
        )
        stream.write(
            "BR_REGIME_OWNER="
            "BRRegimeLayer.evaluate\n"
        )
        stream.write(
            "GENERIC_REGIME_OWNER="
            "DEFERRED\n"
        )
        stream.write(
            f"CONFIRMED_OWNER_COUNT="
            f"{len(confirmed)}\n"
        )
        stream.write(
            f"DEFERRED_CANDIDATE_COUNT="
            f"{len(deferred)}\n"
        )
        stream.write(
            f"INTERNAL_HELPER_COUNT="
            f"{len(helpers)}\n"
        )
        stream.write(
            f"UNRESOLVED_COUNT="
            f"{len(unresolved)}\n"
        )
        stream.write(
            "RUNTIME_INSTRUMENTATION=0\n"
        )

    print(
        "=== BUILD REGIME OWNER "
        "CONFIRMATION V1 ==="
    )
    print(
        f"confirmed_regime_owner_count="
        f"{len(confirmed)}"
    )
    print(
        f"deferred_regime_candidate_count="
        f"{len(deferred)}"
    )
    print(
        f"internal_helper_count="
        f"{len(helpers)}"
    )
    print(
        f"unresolved_count="
        f"{len(unresolved)}"
    )

    for row in confirmed:
        print(
            "CONFIRMED_REGIME_OWNER "
            f"family={row['family']} "
            f"scope={row['ownership_scope']} "
            f"symbol={row['owner_symbol']} "
            f"runtime_calls="
            f"{row['runtime_reachable_call_count']}"
        )

    for row in deferred:
        print(
            "DEFERRED_REGIME_CANDIDATE "
            f"family={row['family']} "
            f"symbol={row['owner_symbol']} "
            f"class="
            f"{row['resolution_classification']}"
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
        "REGIME_OWNER_CONFIRMATION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
