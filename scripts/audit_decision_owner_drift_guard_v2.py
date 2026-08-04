#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import pathlib
import subprocess
from collections import Counter
from typing import Iterable


ROOT = pathlib.Path("/opt/finam-core").resolve()

OUTPUT_DIR = pathlib.Path(
    "/tmp/decision_owner_drift_guard_v2"
)

BASELINE_REGISTRY_FILE = (
    OUTPUT_DIR / "baseline_registry.tsv"
)
BASELINE_EDGES_FILE = (
    OUTPUT_DIR / "baseline_edges.tsv"
)

CURRENT_REGISTRY_SOURCE = pathlib.Path(
    "/tmp/decision_owner_registry_v2/"
    "decision_owner_registry_v2.tsv"
)
CURRENT_EDGES_SOURCE = pathlib.Path(
    "/tmp/decision_owner_registry_v2/"
    "decision_owner_edges_v2.tsv"
)

CURRENT_REGISTRY_FILE = (
    OUTPUT_DIR / "current_registry.tsv"
)
CURRENT_EDGES_FILE = (
    OUTPUT_DIR / "current_edges.tsv"
)
REGISTRY_DRIFT_FILE = (
    OUTPUT_DIR / "registry_drift.tsv"
)
EDGE_DRIFT_FILE = (
    OUTPUT_DIR / "edge_drift.tsv"
)
SUMMARY_FILE = (
    OUTPUT_DIR / "drift_summary.txt"
)
UNRESOLVED_FILE = (
    OUTPUT_DIR / "unresolved.tsv"
)

REGISTRY_FIELDS = (
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

REGISTRY_IDENTITY_FIELDS = (
    "stage",
    "ownership_scope",
    "owner_symbol",
)

REGISTRY_COMPARE_FIELDS = (
    "owner_path",
    "owner_granularity",
    "classification",
    "responsibility",
    "failure_policy",
    "family",
    "ownership_model",
    "owner_confirmed",
    "runtime_instrumentation",
)

EDGE_FIELDS = (
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
)

EDGE_IDENTITY_FIELDS = (
    "source_stage",
    "source_scope",
    "source_owner",
    "target_stage",
    "target_scope",
    "target_owner",
    "classification",
)

EDGE_COMPARE_FIELDS = (
    "reachable",
    "runtime_instrumentation",
)


def run_builder() -> None:
    result = subprocess.run(
        [
            str(ROOT / "venv/bin/python"),
            str(
                ROOT
                / "scripts/"
                "build_decision_owner_registry_v2.py"
            ),
        ],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    print(result.stdout, end="")

    if result.returncode != 0:
        raise RuntimeError(
            "current_registry_builder_failed:"
            f"{result.returncode}"
        )


def read_tsv(
    path: pathlib.Path,
) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(
            f"tsv_missing:{path}"
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


def normalize_rows(
    rows: Iterable[dict[str, str]],
    fields: tuple[str, ...],
    sort_fields: tuple[str, ...],
) -> list[dict[str, str]]:
    normalized = [
        {
            field: row.get(field, "")
            for field in fields
        }
        for row in rows
    ]

    normalized.sort(
        key=lambda row: tuple(
            row[field]
            for field in sort_fields
        )
    )

    return normalized


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


def row_key(
    row: dict[str, str],
    fields: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        row.get(field, "")
        for field in fields
    )


def build_drift(
    *,
    baseline_rows: list[dict[str, str]],
    current_rows: list[dict[str, str]],
    identity_fields: tuple[str, ...],
    compare_fields: tuple[str, ...],
) -> list[dict[str, object]]:
    baseline_index = {
        row_key(row, identity_fields): row
        for row in baseline_rows
    }
    current_index = {
        row_key(row, identity_fields): row
        for row in current_rows
    }

    drift: list[dict[str, object]] = []

    all_keys = sorted(
        set(baseline_index)
        | set(current_index)
    )

    for key in all_keys:
        baseline = baseline_index.get(key)
        current = current_index.get(key)

        identity = "|".join(key)

        if baseline is None:
            drift.append(
                {
                    "identity": identity,
                    "change_type": "ADDED",
                    "field": "",
                    "baseline_value": "",
                    "current_value": "ROW_PRESENT",
                }
            )
            continue

        if current is None:
            drift.append(
                {
                    "identity": identity,
                    "change_type": "REMOVED",
                    "field": "",
                    "baseline_value": "ROW_PRESENT",
                    "current_value": "",
                }
            )
            continue

        for field in compare_fields:
            baseline_value = baseline.get(
                field,
                "",
            )
            current_value = current.get(
                field,
                "",
            )

            if baseline_value == current_value:
                continue

            drift.append(
                {
                    "identity": identity,
                    "change_type": "MODIFIED",
                    "field": field,
                    "baseline_value": baseline_value,
                    "current_value": current_value,
                }
            )

    return drift


def duplicate_identity_count(
    rows: list[dict[str, str]],
    fields: tuple[str, ...],
) -> int:
    counts = Counter(
        row_key(row, fields)
        for row in rows
    )

    return sum(
        1
        for count in counts.values()
        if count > 1
    )


def main() -> int:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not BASELINE_REGISTRY_FILE.is_file():
        raise RuntimeError(
            "baseline_registry_missing:"
            f"{BASELINE_REGISTRY_FILE}"
        )

    if not BASELINE_EDGES_FILE.is_file():
        raise RuntimeError(
            "baseline_edges_missing:"
            f"{BASELINE_EDGES_FILE}"
        )

    skip_builder = (
        os.environ.get(
            "DECISION_OWNER_DRIFT_SKIP_BUILD",
            "0",
        )
        == "1"
    )

    if skip_builder:
        print("current_registry_builder_skipped=1")
    else:
        run_builder()
        print("current_registry_builder_skipped=0")

    baseline_registry = normalize_rows(
        read_tsv(BASELINE_REGISTRY_FILE),
        REGISTRY_FIELDS,
        REGISTRY_IDENTITY_FIELDS,
    )
    baseline_edges = normalize_rows(
        read_tsv(BASELINE_EDGES_FILE),
        EDGE_FIELDS,
        EDGE_IDENTITY_FIELDS,
    )

    current_registry = normalize_rows(
        read_tsv(CURRENT_REGISTRY_SOURCE),
        REGISTRY_FIELDS,
        REGISTRY_IDENTITY_FIELDS,
    )
    current_edges = normalize_rows(
        read_tsv(CURRENT_EDGES_SOURCE),
        EDGE_FIELDS,
        EDGE_IDENTITY_FIELDS,
    )

    write_tsv(
        CURRENT_REGISTRY_FILE,
        REGISTRY_FIELDS,
        current_registry,
    )
    write_tsv(
        CURRENT_EDGES_FILE,
        EDGE_FIELDS,
        current_edges,
    )

    registry_drift = build_drift(
        baseline_rows=baseline_registry,
        current_rows=current_registry,
        identity_fields=REGISTRY_IDENTITY_FIELDS,
        compare_fields=REGISTRY_COMPARE_FIELDS,
    )

    edge_drift = build_drift(
        baseline_rows=baseline_edges,
        current_rows=current_edges,
        identity_fields=EDGE_IDENTITY_FIELDS,
        compare_fields=EDGE_COMPARE_FIELDS,
    )

    baseline_registry_duplicates = (
        duplicate_identity_count(
            baseline_registry,
            REGISTRY_IDENTITY_FIELDS,
        )
    )
    current_registry_duplicates = (
        duplicate_identity_count(
            current_registry,
            REGISTRY_IDENTITY_FIELDS,
        )
    )
    baseline_edge_duplicates = (
        duplicate_identity_count(
            baseline_edges,
            EDGE_IDENTITY_FIELDS,
        )
    )
    current_edge_duplicates = (
        duplicate_identity_count(
            current_edges,
            EDGE_IDENTITY_FIELDS,
        )
    )

    unresolved: list[dict[str, object]] = []

    if baseline_registry_duplicates:
        unresolved.append(
            {
                "scope": "BASELINE_REGISTRY",
                "reason": (
                    "DUPLICATE_REGISTRY_IDENTITY"
                ),
                "count": (
                    baseline_registry_duplicates
                ),
            }
        )

    if current_registry_duplicates:
        unresolved.append(
            {
                "scope": "CURRENT_REGISTRY",
                "reason": (
                    "DUPLICATE_REGISTRY_IDENTITY"
                ),
                "count": (
                    current_registry_duplicates
                ),
            }
        )

    if baseline_edge_duplicates:
        unresolved.append(
            {
                "scope": "BASELINE_EDGES",
                "reason": (
                    "DUPLICATE_EDGE_IDENTITY"
                ),
                "count": baseline_edge_duplicates,
            }
        )

    if current_edge_duplicates:
        unresolved.append(
            {
                "scope": "CURRENT_EDGES",
                "reason": (
                    "DUPLICATE_EDGE_IDENTITY"
                ),
                "count": current_edge_duplicates,
            }
        )

    write_tsv(
        REGISTRY_DRIFT_FILE,
        (
            "identity",
            "change_type",
            "field",
            "baseline_value",
            "current_value",
        ),
        registry_drift,
    )

    write_tsv(
        EDGE_DRIFT_FILE,
        (
            "identity",
            "change_type",
            "field",
            "baseline_value",
            "current_value",
        ),
        edge_drift,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "reason",
            "count",
        ),
        unresolved,
    )

    drift_detected = int(
        bool(
            registry_drift
            or edge_drift
        )
    )

    with SUMMARY_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "DECISION OWNER DRIFT GUARD V2\n"
        )
        stream.write(
            "==============================\n\n"
        )
        stream.write(
            f"baseline_registry_count="
            f"{len(baseline_registry)}\n"
        )
        stream.write(
            f"current_registry_count="
            f"{len(current_registry)}\n"
        )
        stream.write(
            f"baseline_edge_count="
            f"{len(baseline_edges)}\n"
        )
        stream.write(
            f"current_edge_count="
            f"{len(current_edges)}\n"
        )
        stream.write(
            f"registry_drift_count="
            f"{len(registry_drift)}\n"
        )
        stream.write(
            f"edge_drift_count="
            f"{len(edge_drift)}\n"
        )
        stream.write(
            f"drift_detected="
            f"{drift_detected}\n"
        )
        stream.write(
            f"unresolved_count="
            f"{len(unresolved)}\n"
        )
        stream.write(
            "runtime_instrumentation=0\n"
        )

    print(
        "=== AUDIT DECISION OWNER "
        "DRIFT GUARD V2 ==="
    )
    print(
        f"baseline_registry_count="
        f"{len(baseline_registry)}"
    )
    print(
        f"current_registry_count="
        f"{len(current_registry)}"
    )
    print(
        f"baseline_edge_count="
        f"{len(baseline_edges)}"
    )
    print(
        f"current_edge_count="
        f"{len(current_edges)}"
    )
    print(
        f"registry_drift_count="
        f"{len(registry_drift)}"
    )
    print(
        f"edge_drift_count="
        f"{len(edge_drift)}"
    )
    print(
        f"drift_detected={drift_detected}"
    )
    print(
        f"unresolved_count="
        f"{len(unresolved)}"
    )
    print(
        f"current_registry_builder_skipped="
        f"{int(skip_builder)}"
    )

    for row in registry_drift:
        print(
            f"REGISTRY_DRIFT "
            f"identity={row['identity']} "
            f"type={row['change_type']} "
            f"field={row['field']} "
            f"baseline={row['baseline_value']} "
            f"current={row['current_value']}"
        )

    for row in edge_drift:
        print(
            f"EDGE_DRIFT "
            f"identity={row['identity']} "
            f"type={row['change_type']} "
            f"field={row['field']} "
            f"baseline={row['baseline_value']} "
            f"current={row['current_value']}"
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

    if unresolved:
        print(
            "VERDICT="
            "DECISION_OWNER_DRIFT_GUARD_V2_UNRESOLVED"
        )
        return 2

    if drift_detected:
        print(
            "VERDICT="
            "DECISION_OWNER_DRIFT_GUARD_V2_DRIFT_DETECTED"
        )
        return 1

    print(
        "VERDICT="
        "DECISION_OWNER_DRIFT_GUARD_V2_OK"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
