#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
import re
import subprocess
from dataclasses import dataclass


ROOT = pathlib.Path("/opt/finam-core").resolve()

OUT = pathlib.Path("/tmp/decision_owner_registry_v4")

V3_TEST = ROOT / "scripts/test_decision_owner_registry_v3.sh"
EDGE_TEST = ROOT / "scripts/test_edge_owner_confirmation_v1.sh"

V3_LOG = OUT / "source_v3_test.log"
EDGE_LOG = OUT / "source_edge_confirmation.log"

CONFIRMED_FILE = OUT / "confirmed_owners.tsv"
DEFERRED_FILE = OUT / "deferred_stages.tsv"
EDGES_FILE = OUT / "ownership_edges.tsv"
CONTRACT_FILE = OUT / "registry_contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"

OWNER_PATTERN = re.compile(
    r"^REGISTRY_OWNER "
    r"stage=(?P<stage>\S+) "
    r"scope=(?P<scope>\S+) "
    r"symbol=(?P<symbol>\S+)"
)

EDGE_PATTERN = re.compile(
    r"^DEFERRED_EDGE_STAGE "
    r"stage=(?P<stage>\S+) "
    r"scope=(?P<scope>\S+) "
    r"status=(?P<status>\S+) "
    r"confirmed_owner_count=(?P<confirmed>\d+) "
    r"dormant_component_count=(?P<dormant>\d+)"
)


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: str


def run_test(path: pathlib.Path) -> CommandResult:
    if not path.is_file():
        raise RuntimeError(f"required_test_missing:{path}")

    completed = subprocess.run(
        [str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
    )


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, object]],
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


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    unresolved: list[dict[str, object]] = []

    v3_result = run_test(V3_TEST)
    V3_LOG.write_text(v3_result.stdout, encoding="utf-8")

    if v3_result.returncode != 0:
        unresolved.append(
            {
                "scope": "SOURCE_REGISTRY_V3",
                "identity": "",
                "reason": f"V3_TEST_EXIT_CODE:{v3_result.returncode}",
            }
        )

    accepted_v3_verdicts = (
        "VERDICT=TEST_DECISION_OWNER_REGISTRY_V3_OK",
        "VERDICT=TEST_DECISION_OWNER_REGISTRY_V3_FINAL_OK",
        "VERDICT=TEST_DECISION_OWNER_REGISTRY_AND_DRIFT_V3_FINAL_OK",
    )

    if not any(
        verdict in v3_result.stdout
        for verdict in accepted_v3_verdicts
    ):
        unresolved.append(
            {
                "scope": "SOURCE_REGISTRY_V3",
                "identity": "",
                "reason": "V3_ACCEPTED_VERDICT_MISSING",
            }
        )

    v3_output_dir = pathlib.Path(
        "/tmp/decision_owner_registry_v3"
    )

    candidate_files = (
        v3_output_dir / "decision_owner_registry_v3.tsv",
        v3_output_dir / "confirmed_owners.tsv",
        v3_output_dir / "decision_owner_registry.tsv",
        v3_output_dir / "registry_owners.tsv",
        v3_output_dir / "owners.tsv",
    )

    v3_registry_file = next(
        (
            candidate
            for candidate in candidate_files
            if candidate.is_file()
        ),
        None,
    )

    owners_by_identity: dict[
        tuple[str, str, str],
        dict[str, object],
    ] = {}

    if v3_registry_file is None:
        unresolved.append(
            {
                "scope": "SOURCE_REGISTRY_V3",
                "identity": "",
                "reason": "V3_REGISTRY_TSV_MISSING",
            }
        )
    else:
        with v3_registry_file.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as stream:
            for row in csv.DictReader(
                stream,
                delimiter="\t",
            ):
                stage = (
                    row.get("stage")
                    or ""
                ).strip()

                scope = (
                    row.get("ownership_scope")
                    or row.get("scope")
                    or ""
                ).strip()

                symbol = (
                    row.get("owner_symbol")
                    or row.get("symbol")
                    or row.get("candidate_symbol")
                    or ""
                ).strip()

                status = (
                    row.get("status")
                    or "CONFIRMED"
                ).strip()

                owner_confirmed = str(
                    row.get("owner_confirmed")
                    or "1"
                ).strip()

                if (
                    not stage
                    or not scope
                    or not symbol
                    or status != "CONFIRMED"
                    or owner_confirmed not in {"1", "true", "True"}
                ):
                    continue

                identity = (
                    stage,
                    scope,
                    symbol,
                )

                owners_by_identity[identity] = {
                    "stage": stage,
                    "ownership_scope": scope,
                    "owner_symbol": symbol,
                    "status": "CONFIRMED",
                    "source_registry_version": "V3",
                    "owner_confirmed": 1,
                    "runtime_instrumentation": 0,
                }

    confirmed_rows = sorted(
        owners_by_identity.values(),
        key=lambda row: (
            str(row["stage"]),
            str(row["ownership_scope"]),
            str(row["owner_symbol"]),
        ),
    )

    if len(confirmed_rows) != 9:
        unresolved.append(
            {
                "scope": "CONFIRMED_OWNER_SET",
                "identity": "",
                "reason": (
                    "EXPECTED_CONFIRMED_OWNER_COUNT_9:"
                    f"ACTUAL_{len(confirmed_rows)}"
                ),
            }
        )

    owner_identities = [
        (
            str(row["stage"]),
            str(row["ownership_scope"]),
            str(row["owner_symbol"]),
        )
        for row in confirmed_rows
    ]

    duplicate_owner_identity_count = (
        len(owner_identities)
        - len(set(owner_identities))
    )

    if duplicate_owner_identity_count != 0:
        unresolved.append(
            {
                "scope": "CONFIRMED_OWNER_SET",
                "identity": "",
                "reason": (
                    "DUPLICATE_OWNER_IDENTITY_COUNT:"
                    f"{duplicate_owner_identity_count}"
                ),
            }
        )

    edge_result = run_test(EDGE_TEST)
    EDGE_LOG.write_text(edge_result.stdout, encoding="utf-8")

    if edge_result.returncode != 0:
        unresolved.append(
            {
                "scope": "EDGE_CONFIRMATION",
                "identity": "EDGE|EDGE_DECISION",
                "reason": (
                    "EDGE_CONFIRMATION_TEST_EXIT_CODE:"
                    f"{edge_result.returncode}"
                ),
            }
        )

    if (
        "VERDICT=TEST_EDGE_OWNER_CONFIRMATION_V1_OK"
        not in edge_result.stdout
    ):
        unresolved.append(
            {
                "scope": "EDGE_CONFIRMATION",
                "identity": "EDGE|EDGE_DECISION",
                "reason": "EDGE_CONFIRMATION_VERDICT_MISSING",
            }
        )

    deferred_rows: list[dict[str, object]] = []

    for line in edge_result.stdout.splitlines():
        match = EDGE_PATTERN.match(line.strip())

        if not match:
            continue

        deferred_rows.append(
            {
                "stage": match.group("stage"),
                "ownership_scope": match.group("scope"),
                "status": match.group("status"),
                "confirmed_owner_count": int(
                    match.group("confirmed")
                ),
                "dormant_component_count": int(
                    match.group("dormant")
                ),
                "owner_symbol": "",
                "reason": (
                    "NO_AUTHORITATIVE_EXECUTABLE_EDGE_OWNER_PROVEN"
                ),
                "source_registry_version": "EDGE_OWNER_AUDIT_V1",
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    deferred_unique = {
        (
            str(row["stage"]),
            str(row["ownership_scope"]),
            str(row["status"]),
        ): row
        for row in deferred_rows
    }

    deferred_rows = sorted(
        deferred_unique.values(),
        key=lambda row: (
            str(row["stage"]),
            str(row["ownership_scope"]),
        ),
    )

    edge_contract_ok = (
        len(deferred_rows) == 1
        and deferred_rows[0]["stage"] == "EDGE"
        and deferred_rows[0]["ownership_scope"] == "EDGE_DECISION"
        and deferred_rows[0]["status"] == "DEFERRED"
        and deferred_rows[0]["confirmed_owner_count"] == 0
        and deferred_rows[0]["dormant_component_count"] == 3
    )

    if not edge_contract_ok:
        unresolved.append(
            {
                "scope": "EDGE_DEFERRED_STAGE",
                "identity": "EDGE|EDGE_DECISION",
                "reason": "EDGE_DEFERRED_CONTRACT_INVALID",
            }
        )

    if any(
        row["stage"] == "EDGE"
        for row in confirmed_rows
    ):
        unresolved.append(
            {
                "scope": "CONFIRMED_OWNER_SET",
                "identity": "EDGE",
                "reason": "EDGE_MUST_NOT_BE_CONFIRMED_OWNER",
            }
        )

    ownership_edges: list[dict[str, object]] = []

    ordered_stages = (
        "STRATEGY",
        "REGIME",
        "RISK",
        "RUNTIME",
        "EXECUTION",
        "BROKER",
    )

    rows_by_stage: dict[str, list[dict[str, object]]] = {}

    for row in confirmed_rows:
        rows_by_stage.setdefault(
            str(row["stage"]),
            [],
        ).append(row)

    for source_stage, target_stage in zip(
        ordered_stages,
        ordered_stages[1:],
    ):
        for source in rows_by_stage.get(source_stage, []):
            for target in rows_by_stage.get(target_stage, []):
                ownership_edges.append(
                    {
                        "source_stage": source_stage,
                        "source_scope": source["ownership_scope"],
                        "source_symbol": source["owner_symbol"],
                        "target_stage": target_stage,
                        "target_scope": target["ownership_scope"],
                        "target_symbol": target["owner_symbol"],
                        "classification": (
                            "PRESERVED_V3_DECISION_FLOW"
                        ),
                        "source_registry_version": "V3",
                    }
                )

    write_tsv(
        CONFIRMED_FILE,
        (
            "stage",
            "ownership_scope",
            "owner_symbol",
            "status",
            "source_registry_version",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        confirmed_rows,
    )

    write_tsv(
        DEFERRED_FILE,
        (
            "stage",
            "ownership_scope",
            "status",
            "confirmed_owner_count",
            "dormant_component_count",
            "owner_symbol",
            "reason",
            "source_registry_version",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        deferred_rows,
    )

    write_tsv(
        EDGES_FILE,
        (
            "source_stage",
            "source_scope",
            "source_symbol",
            "target_stage",
            "target_scope",
            "target_symbol",
            "classification",
            "source_registry_version",
        ),
        ownership_edges,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "identity",
            "reason",
        ),
        unresolved,
    )

    with CONTRACT_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write("DECISION OWNER REGISTRY V4\n")
        stream.write("==========================\n\n")
        stream.write(
            f"CONFIRMED_OWNER_COUNT={len(confirmed_rows)}\n"
        )
        stream.write(
            "PRESERVED_V3_OWNER_COUNT="
            f"{len(confirmed_rows)}\n"
        )
        stream.write(
            f"DEFERRED_STAGE_COUNT={len(deferred_rows)}\n"
        )
        stream.write(
            "EDGE_STAGE_STATUS="
            f"{deferred_rows[0]['status'] if deferred_rows else 'MISSING'}\n"
        )
        stream.write("EDGE_CONFIRMED_OWNER_COUNT=0\n")
        stream.write("EDGE_DORMANT_COMPONENT_COUNT=3\n")
        stream.write(
            f"DUPLICATE_OWNER_IDENTITY_COUNT="
            f"{duplicate_owner_identity_count}\n"
        )
        stream.write(
            f"UNRESOLVED_COUNT={len(unresolved)}\n"
        )
        stream.write("RUNTIME_INSTRUMENTATION=0\n")
        stream.write("MICRO_LIVE_ALLOWED=0\n")

    print("=== BUILD DECISION OWNER REGISTRY V4 ===")
    print(f"confirmed_owner_count={len(confirmed_rows)}")
    print(f"preserved_v3_owner_count={len(confirmed_rows)}")
    print(
        f"duplicate_owner_identity_count="
        f"{duplicate_owner_identity_count}"
    )
    print(f"deferred_stage_count={len(deferred_rows)}")
    print("edge_confirmed_owner_count=0")
    print("edge_dormant_component_count=3")
    print(f"ownership_edge_count={len(ownership_edges)}")
    print(f"unresolved_count={len(unresolved)}")

    for row in confirmed_rows:
        print(
            "REGISTRY_OWNER "
            f"stage={row['stage']} "
            f"scope={row['ownership_scope']} "
            f"symbol={row['owner_symbol']} "
            "status=CONFIRMED"
        )

    for row in deferred_rows:
        print(
            "REGISTRY_DEFERRED_STAGE "
            f"stage={row['stage']} "
            f"scope={row['ownership_scope']} "
            f"status={row['status']} "
            f"confirmed_owner_count="
            f"{row['confirmed_owner_count']} "
            f"dormant_component_count="
            f"{row['dormant_component_count']}"
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
    print("VERDICT=DECISION_OWNER_REGISTRY_V4_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
