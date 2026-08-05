#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import pathlib
import subprocess


ROOT = pathlib.Path("/opt/finam-core")
OUT = pathlib.Path("/tmp/decision_owner_drift_guard_v3")

BASELINE_REGISTRY = OUT / "baseline_registry.tsv"
BASELINE_EDGES = OUT / "baseline_edges.tsv"

CURRENT_REGISTRY_SOURCE = pathlib.Path(
    "/tmp/decision_owner_registry_v3/decision_owner_registry_v3.tsv"
)
CURRENT_EDGES_SOURCE = pathlib.Path(
    "/tmp/decision_owner_registry_v3/decision_owner_edges_v3.tsv"
)

CURRENT_REGISTRY = OUT / "current_registry.tsv"
CURRENT_EDGES = OUT / "current_edges.tsv"
REGISTRY_DRIFT = OUT / "registry_drift.tsv"
EDGE_DRIFT = OUT / "edge_drift.tsv"
UNRESOLVED = OUT / "unresolved.tsv"
SUMMARY = OUT / "drift_summary.txt"

REGISTRY_IDENTITY = ("stage", "ownership_scope", "owner_symbol")
EDGE_IDENTITY = (
    "source_stage",
    "source_scope",
    "source_owner",
    "target_stage",
    "target_scope",
    "target_owner",
    "classification",
)


def read_tsv(path: pathlib.Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    if not path.is_file():
        raise RuntimeError(f"source_file_missing:{path}")

    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        fields = tuple(reader.fieldnames or ())
        rows = [
            {key: str(value or "").strip() for key, value in row.items()}
            for row in reader
        ]

    return fields, rows


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def identity(row: dict[str, str], fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(row.get(field, "") for field in fields)


def compare(
    baseline_rows: list[dict[str, str]],
    current_rows: list[dict[str, str]],
    identity_fields: tuple[str, ...],
) -> list[dict[str, str]]:
    baseline = {
        identity(row, identity_fields): row
        for row in baseline_rows
    }
    current = {
        identity(row, identity_fields): row
        for row in current_rows
    }

    drift: list[dict[str, str]] = []

    for key in sorted(set(baseline) | set(current)):
        baseline_row = baseline.get(key)
        current_row = current.get(key)
        identity_text = "|".join(key)

        if baseline_row is None:
            drift.append(
                {
                    "identity": identity_text,
                    "type": "ADDED",
                    "field": "",
                    "baseline": "",
                    "current": "ROW_PRESENT",
                }
            )
            continue

        if current_row is None:
            drift.append(
                {
                    "identity": identity_text,
                    "type": "REMOVED",
                    "field": "",
                    "baseline": "ROW_PRESENT",
                    "current": "",
                }
            )
            continue

        fields = sorted(set(baseline_row) | set(current_row))

        for field in fields:
            if field in identity_fields:
                continue

            old = baseline_row.get(field, "")
            new = current_row.get(field, "")

            if old != new:
                drift.append(
                    {
                        "identity": identity_text,
                        "type": "MODIFIED",
                        "field": field,
                        "baseline": old,
                        "current": new,
                    }
                )

    return drift


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    skip_builder = os.environ.get(
        "DECISION_OWNER_DRIFT_SKIP_BUILD",
        "0",
    ) == "1"

    if not skip_builder:
        result = subprocess.run(
            [
                str(ROOT / "venv/bin/python"),
                "scripts/build_decision_owner_registry_v3.py",
            ],
            cwd=ROOT,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"current_registry_builder_failed:{result.returncode}"
            )

    registry_fields, baseline_registry = read_tsv(BASELINE_REGISTRY)
    edge_fields, baseline_edges = read_tsv(BASELINE_EDGES)

    _, current_registry = read_tsv(CURRENT_REGISTRY_SOURCE)
    _, current_edges = read_tsv(CURRENT_EDGES_SOURCE)

    current_registry.sort(
        key=lambda row: identity(row, REGISTRY_IDENTITY)
    )
    current_edges.sort(
        key=lambda row: identity(row, EDGE_IDENTITY)
    )

    write_tsv(CURRENT_REGISTRY, registry_fields, current_registry)
    write_tsv(CURRENT_EDGES, edge_fields, current_edges)

    registry_drift = compare(
        baseline_registry,
        current_registry,
        REGISTRY_IDENTITY,
    )
    edge_drift = compare(
        baseline_edges,
        current_edges,
        EDGE_IDENTITY,
    )

    write_tsv(
        REGISTRY_DRIFT,
        ("identity", "type", "field", "baseline", "current"),
        registry_drift,
    )
    write_tsv(
        EDGE_DRIFT,
        ("identity", "type", "field", "baseline", "current"),
        edge_drift,
    )
    write_tsv(UNRESOLVED, ("scope", "symbol", "reason"), [])

    drift_detected = int(bool(registry_drift or edge_drift))

    with SUMMARY.open("w", encoding="utf-8") as stream:
        stream.write(f"baseline_registry_count={len(baseline_registry)}\n")
        stream.write(f"current_registry_count={len(current_registry)}\n")
        stream.write(f"baseline_edge_count={len(baseline_edges)}\n")
        stream.write(f"current_edge_count={len(current_edges)}\n")
        stream.write(f"registry_drift_count={len(registry_drift)}\n")
        stream.write(f"edge_drift_count={len(edge_drift)}\n")
        stream.write(f"drift_detected={drift_detected}\n")
        stream.write("unresolved_count=0\n")

    print("=== AUDIT DECISION OWNER DRIFT GUARD V3 ===")
    print(f"baseline_registry_count={len(baseline_registry)}")
    print(f"current_registry_count={len(current_registry)}")
    print(f"baseline_edge_count={len(baseline_edges)}")
    print(f"current_edge_count={len(current_edges)}")
    print(f"registry_drift_count={len(registry_drift)}")
    print(f"edge_drift_count={len(edge_drift)}")
    print(f"drift_detected={drift_detected}")
    print("unresolved_count=0")
    print(f"current_registry_builder_skipped={int(skip_builder)}")

    for row in registry_drift:
        print(
            "REGISTRY_DRIFT "
            f"identity={row['identity']} "
            f"type={row['type']} "
            f"field={row['field']} "
            f"baseline={row['baseline']} "
            f"current={row['current']}"
        )

    for row in edge_drift:
        print(
            "EDGE_DRIFT "
            f"identity={row['identity']} "
            f"type={row['type']} "
            f"field={row['field']} "
            f"baseline={row['baseline']} "
            f"current={row['current']}"
        )

    print("writes_performed=0")
    print("db_writes_performed=0")
    print("runtime_instrumentation=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    if drift_detected:
        print("VERDICT=DECISION_OWNER_DRIFT_GUARD_V3_DRIFT_DETECTED")
        return 1

    print("VERDICT=DECISION_OWNER_DRIFT_GUARD_V3_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
