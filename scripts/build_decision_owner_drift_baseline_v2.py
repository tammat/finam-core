#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
import subprocess


ROOT = pathlib.Path("/opt/finam-core").resolve()

BASELINE_TAG = "checkpoint_strategy_owner_audit_v1"
EXPECTED_BASELINE_COMMIT = (
    "a0e421360cece69c2226060c07a2674cdfba4cfb"
)

REGISTRY_SOURCE = pathlib.Path(
    "/tmp/decision_owner_registry_v2/"
    "decision_owner_registry_v2.tsv"
)

EDGES_SOURCE = pathlib.Path(
    "/tmp/decision_owner_registry_v2/"
    "decision_owner_edges_v2.tsv"
)

OUTPUT_DIR = pathlib.Path(
    "/tmp/decision_owner_drift_guard_v2"
)

BASELINE_REGISTRY_FILE = (
    OUTPUT_DIR / "baseline_registry.tsv"
)

BASELINE_EDGES_FILE = (
    OUTPUT_DIR / "baseline_edges.tsv"
)

BASELINE_METADATA_FILE = (
    OUTPUT_DIR / "baseline_metadata.txt"
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


def git_text(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "git_command_failed:"
            f"command={' '.join(args)}:"
            f"returncode={result.returncode}:"
            f"output={result.stdout.strip()}"
        )

    return result.stdout.strip()


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


def normalize_rows(
    rows: list[dict[str, str]],
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
    rows: list[dict[str, str]],
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

    baseline_commit = git_text(
        "rev-list",
        "-n",
        "1",
        BASELINE_TAG,
    )

    if baseline_commit != EXPECTED_BASELINE_COMMIT:
        raise RuntimeError(
            "baseline_commit_mismatch:"
            f"actual={baseline_commit}:"
            f"expected={EXPECTED_BASELINE_COMMIT}"
        )

    registry_rows = normalize_rows(
        read_tsv(REGISTRY_SOURCE),
        REGISTRY_FIELDS,
        (
            "stage",
            "ownership_scope",
            "owner_symbol",
        ),
    )

    edge_rows = normalize_rows(
        read_tsv(EDGES_SOURCE),
        EDGE_FIELDS,
        (
            "source_stage",
            "source_scope",
            "source_owner",
            "target_stage",
            "target_scope",
            "target_owner",
            "classification",
        ),
    )

    write_tsv(
        BASELINE_REGISTRY_FILE,
        REGISTRY_FIELDS,
        registry_rows,
    )

    write_tsv(
        BASELINE_EDGES_FILE,
        EDGE_FIELDS,
        edge_rows,
    )

    with BASELINE_METADATA_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            f"baseline_tag={BASELINE_TAG}\n"
        )
        stream.write(
            f"baseline_commit={baseline_commit}\n"
        )
        stream.write(
            f"baseline_registry_rows="
            f"{len(registry_rows)}\n"
        )
        stream.write(
            f"baseline_edge_rows="
            f"{len(edge_rows)}\n"
        )
        stream.write(
            "strategy_family_scoped=1\n"
        )
        stream.write(
            "runtime_instrumentation=0\n"
        )

    print(
        "=== BUILD DECISION OWNER "
        "DRIFT BASELINE V2 ==="
    )
    print(f"baseline_tag={BASELINE_TAG}")
    print(
        f"baseline_commit={baseline_commit}"
    )
    print(
        f"baseline_registry_rows="
        f"{len(registry_rows)}"
    )
    print(
        f"baseline_edge_rows="
        f"{len(edge_rows)}"
    )
    print("strategy_family_scoped=1")
    print(
        f"baseline_registry_file="
        f"{BASELINE_REGISTRY_FILE}"
    )
    print(
        f"baseline_edges_file="
        f"{BASELINE_EDGES_FILE}"
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
        "DECISION_OWNER_DRIFT_BASELINE_V2_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
