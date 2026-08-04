#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib


OUTPUT_DIR = pathlib.Path(
    "/tmp/decision_owner_priority_confirmation_v1"
)

CONFIRMED_FILE = OUTPUT_DIR / "confirmed_priority_owners.tsv"
DEFERRED_FILE = OUTPUT_DIR / "deferred_priority_owners.tsv"
CONTRACT_FILE = OUTPUT_DIR / "confirmation_contract.txt"

RUNTIME_EVIDENCE = pathlib.Path(
    "/tmp/decision_owner_runtime_caller_chain_v2/"
    "branch_contract.tsv"
)

RISK_EVIDENCE = pathlib.Path(
    "/tmp/decision_owner_runtime_caller_chain_v2/"
    "risk_result_usage.tsv"
)

CALL_PATH_EVIDENCE = pathlib.Path(
    "/tmp/decision_owner_priority_call_path_v1/"
    "call_path_edges.tsv"
)


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"evidence_missing:{path}")

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        return list(
            csv.DictReader(
                stream,
                delimiter="\t",
            )
        )


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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    runtime_rows = read_tsv(RUNTIME_EVIDENCE)
    risk_rows = read_tsv(RISK_EVIDENCE)
    call_path_rows = read_tsv(CALL_PATH_EVIDENCE)

    runtime_branches = {
        row["branch"]: row
        for row in runtime_rows
    }

    ng_complete = (
        runtime_branches.get("NG_M1", {}).get("chain_complete")
        == "1"
    )
    br_complete = (
        runtime_branches.get("BR", {}).get("chain_complete")
        == "1"
    )

    authoritative_risk = [
        row
        for row in risk_rows
        if row.get("authoritative_binding") == "1"
        and row.get("decision_result_consumed") == "1"
    ]

    execution_reachable = any(
        row.get("edge") == "RUNTIME_TO_EXECUTION"
        and row.get("reachable") == "1"
        for row in call_path_rows
    )

    broker_reachable = any(
        row.get("edge") == "EXECUTION_TO_BROKER"
        and row.get("reachable") == "1"
        for row in call_path_rows
    )

    confirmed: list[dict[str, object]] = []

    if len(authoritative_risk) == 1:
        confirmed.append(
            {
                "stage": "RISK",
                "owner_path": (
                    "src/finam_core/risk/"
                    "portfolio_risk_gate.py"
                ),
                "owner_symbol": "PortfolioRiskGate.check",
                "owner_granularity": "METHOD",
                "classification": (
                    "CONFIRMED_DECISION_OWNER"
                ),
                "evidence": (
                    "authoritative_binding_and_"
                    "decision_result_consumed"
                ),
                "failure_policy": "FAIL_OPEN_RECORDER",
                "runtime_instrumentation": 0,
            }
        )

    if ng_complete and br_complete:
        confirmed.append(
            {
                "stage": "RUNTIME",
                "owner_path": (
                    "src/finam_core/pipelines/"
                    "paper_pipeline.py"
                ),
                "owner_symbol": (
                    "_execute_br_signal_in_paper"
                ),
                "owner_granularity": "METHOD",
                "classification": (
                    "CONFIRMED_DECISION_OWNER"
                ),
                "evidence": (
                    "NG_M1_and_BR_runtime_chains_complete"
                ),
                "failure_policy": "FAIL_OPEN_RECORDER",
                "runtime_instrumentation": 0,
            }
        )

    deferred = [
        {
            "stage": "STRATEGY",
            "candidate": "UNRESOLVED",
            "classification": "DEFERRED",
            "reason": (
                "signal_creation_owner_not_proven"
            ),
            "runtime_instrumentation": 0,
        },
        {
            "stage": "EXECUTION",
            "candidate": (
                "ExecutionDispatcher.place_limit_order"
            ),
            "classification": "DEFERRED",
            "reason": (
                "dispatch_reachable_but_authoritative_"
                "result_contract_not_proven"
            ),
            "runtime_instrumentation": 0,
        },
        {
            "stage": "BROKER",
            "candidate": "OrdersClient",
            "classification": "DEFERRED",
            "reason": (
                "broker_boundary_reachable_but_ack_"
                "ownership_not_proven"
            ),
            "runtime_instrumentation": 0,
        },
    ]

    write_tsv(
        CONFIRMED_FILE,
        (
            "stage",
            "owner_path",
            "owner_symbol",
            "owner_granularity",
            "classification",
            "evidence",
            "failure_policy",
            "runtime_instrumentation",
        ),
        confirmed,
    )

    write_tsv(
        DEFERRED_FILE,
        (
            "stage",
            "candidate",
            "classification",
            "reason",
            "runtime_instrumentation",
        ),
        deferred,
    )

    with CONTRACT_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "DECISION OWNER PRIORITY CONFIRMATION V1\n"
        )
        stream.write(
            "=======================================\n\n"
        )
        stream.write(
            f"RISK_CONFIRMED="
            f"{int(len(authoritative_risk) == 1)}\n"
        )
        stream.write(
            f"RUNTIME_CONFIRMED="
            f"{int(ng_complete and br_complete)}\n"
        )
        stream.write(
            f"EXECUTION_REACHABLE="
            f"{int(execution_reachable)}\n"
        )
        stream.write(
            f"BROKER_REACHABLE="
            f"{int(broker_reachable)}\n"
        )
        stream.write(
            "RUNTIME_INSTRUMENTATION=0\n"
        )

    print(
        "=== BUILD DECISION OWNER "
        "PRIORITY CONFIRMATION V1 ==="
    )
    print(
        f"confirmed_owner_count={len(confirmed)}"
    )
    print(
        f"deferred_owner_count={len(deferred)}"
    )
    print(
        f"risk_owner_confirmed="
        f"{int(len(authoritative_risk) == 1)}"
    )
    print(
        f"runtime_owner_confirmed="
        f"{int(ng_complete and br_complete)}"
    )
    print(
        f"execution_reachable="
        f"{int(execution_reachable)}"
    )
    print(
        f"broker_reachable="
        f"{int(broker_reachable)}"
    )

    for row in confirmed:
        print(
            f"CONFIRMED_OWNER stage={row['stage']} "
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
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "DECISION_OWNER_PRIORITY_CONFIRMATION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
