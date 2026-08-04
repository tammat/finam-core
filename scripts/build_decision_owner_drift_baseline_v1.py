#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import pathlib
import subprocess
import tempfile
from typing import Iterable


ROOT = pathlib.Path("/opt/finam-core").resolve()

BASELINE_TAG = "checkpoint_decision_owner_registry_v1"
EXPECTED_BASELINE_COMMIT = (
    "149742a9fb63b314846beb27acd0664bcb53da6a"
)

REGISTRY_BUILDER = "scripts/build_decision_owner_registry_v1.py"

OUTPUT_DIR = pathlib.Path(
    "/tmp/decision_owner_drift_guard_v1"
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

GENERATED_REGISTRY_RELATIVE = (
    "decision_owner_registry_v1/"
    "decision_owner_registry_v1.tsv"
)

GENERATED_EDGES_RELATIVE = (
    "decision_owner_registry_v1/"
    "decision_owner_edges_v1.tsv"
)


def run(
    args: list[str],
    *,
    cwd: pathlib.Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "command_failed:"
            f"returncode={result.returncode}:"
            f"command={' '.join(args)}:"
            f"output={result.stdout}"
        )

    return result


def git_text(*args: str) -> str:
    return run(
        ["git", *args],
        cwd=ROOT,
    ).stdout.strip()


def normalize_rows(
    rows: Iterable[dict[str, str]],
    fields: tuple[str, ...],
    sort_fields: tuple[str, ...],
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []

    for source in rows:
        row = {
            field: str(source.get(field, "")).strip()
            for field in fields
        }
        normalized.append(row)

    normalized.sort(
        key=lambda row: tuple(
            row[field]
            for field in sort_fields
        )
    )

    return normalized


def read_tsv_text(
    text: str,
) -> list[dict[str, str]]:
    stream = io.StringIO(text)
    return list(
        csv.DictReader(
            stream,
            delimiter="\t",
        )
    )


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

    builder_text = git_text(
        "show",
        f"{BASELINE_TAG}:{REGISTRY_BUILDER}",
    )

    with tempfile.TemporaryDirectory(
        prefix="decision_owner_baseline_v1_"
    ) as temp_dir_raw:
        temp_dir = pathlib.Path(temp_dir_raw)

        builder_path = (
            temp_dir
            / "build_decision_owner_registry_v1.py"
        )
        builder_path.write_text(
            builder_text,
            encoding="utf-8",
        )

        # Builder использует уже подтверждённые evidence-артефакты
        # в /tmp. Они воспроизводятся текущими durable audit-скриптами
        # до вызова baseline builder в общем тесте.
        run(
            [
                str(ROOT / "venv/bin/python"),
                str(builder_path),
            ],
            cwd=ROOT,
        )

    generated_dir = pathlib.Path(
        "/tmp/decision_owner_registry_v1"
    )

    generated_registry = (
        generated_dir
        / "decision_owner_registry_v1.tsv"
    )
    generated_edges = (
        generated_dir
        / "decision_owner_edges_v1.tsv"
    )

    if not generated_registry.is_file():
        raise RuntimeError(
            f"generated_registry_missing:"
            f"{generated_registry}"
        )

    if not generated_edges.is_file():
        raise RuntimeError(
            f"generated_edges_missing:"
            f"{generated_edges}"
        )

    registry_fields = (
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

    edge_fields = (
        "edge_order",
        "source_stage",
        "source_owner",
        "target_stage",
        "target_owner",
        "classification",
        "reachable",
        "runtime_instrumentation",
    )

    with generated_registry.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        registry_rows = normalize_rows(
            csv.DictReader(
                stream,
                delimiter="\t",
            ),
            registry_fields,
            (
                "stage",
                "ownership_scope",
                "owner_symbol",
            ),
        )

    with generated_edges.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        edge_rows = normalize_rows(
            csv.DictReader(
                stream,
                delimiter="\t",
            ),
            edge_fields,
            (
                "edge_order",
                "source_stage",
                "target_stage",
                "classification",
            ),
        )

    write_tsv(
        BASELINE_REGISTRY_FILE,
        registry_fields,
        registry_rows,
    )
    write_tsv(
        BASELINE_EDGES_FILE,
        edge_fields,
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
            "runtime_instrumentation=0\n"
        )

    print(
        "=== BUILD DECISION OWNER "
        "DRIFT BASELINE V1 ==="
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
        f"baseline_edge_rows={len(edge_rows)}"
    )
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
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "DECISION_OWNER_DRIFT_BASELINE_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
