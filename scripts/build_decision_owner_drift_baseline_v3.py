#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
import subprocess


ROOT = pathlib.Path("/opt/finam-core")
OUT = pathlib.Path("/tmp/decision_owner_drift_guard_v3")
REGISTRY_SOURCE = pathlib.Path(
    "/tmp/decision_owner_registry_v3/decision_owner_registry_v3.tsv"
)
EDGES_SOURCE = pathlib.Path(
    "/tmp/decision_owner_registry_v3/decision_owner_edges_v3.tsv"
)

BASELINE_TAG = "checkpoint_regime_owner_audit_v1"
EXPECTED_COMMIT = "9eb56d4b25bf553b085a296831c5eac30e4dae6b"


def git_text(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"git_failed:{' '.join(args)}:{result.stdout.strip()}"
        )

    return result.stdout.strip()


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
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    commit = git_text("rev-list", "-n", "1", BASELINE_TAG)

    if commit != EXPECTED_COMMIT:
        raise RuntimeError(
            f"baseline_commit_mismatch:actual={commit}:expected={EXPECTED_COMMIT}"
        )

    registry_fields, registry_rows = read_tsv(REGISTRY_SOURCE)
    edge_fields, edge_rows = read_tsv(EDGES_SOURCE)

    registry_rows.sort(
        key=lambda row: (
            row["stage"],
            row["ownership_scope"],
            row["owner_symbol"],
        )
    )

    edge_rows.sort(
        key=lambda row: (
            row["source_stage"],
            row["source_scope"],
            row["source_owner"],
            row["target_stage"],
            row["target_scope"],
            row["target_owner"],
            row["classification"],
        )
    )

    write_tsv(OUT / "baseline_registry.tsv", registry_fields, registry_rows)
    write_tsv(OUT / "baseline_edges.tsv", edge_fields, edge_rows)

    with (OUT / "baseline_metadata.txt").open("w", encoding="utf-8") as stream:
        stream.write(f"baseline_tag={BASELINE_TAG}\n")
        stream.write(f"baseline_commit={commit}\n")
        stream.write(f"baseline_registry_rows={len(registry_rows)}\n")
        stream.write(f"baseline_edge_rows={len(edge_rows)}\n")
        stream.write("registry_version=V3\n")
        stream.write("regime_family_scoped=1\n")
        stream.write("runtime_instrumentation=0\n")

    print("=== BUILD DECISION OWNER DRIFT BASELINE V3 ===")
    print(f"baseline_tag={BASELINE_TAG}")
    print(f"baseline_commit={commit}")
    print(f"baseline_registry_rows={len(registry_rows)}")
    print(f"baseline_edge_rows={len(edge_rows)}")
    print("registry_version=V3")
    print("runtime_instrumentation=0")
    print("VERDICT=DECISION_OWNER_DRIFT_BASELINE_V3_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
