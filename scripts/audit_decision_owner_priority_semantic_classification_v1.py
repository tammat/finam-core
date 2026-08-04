#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
from dataclasses import dataclass


ROOT = pathlib.Path("/opt/finam-core").resolve()

INPUT = pathlib.Path(
    "/tmp/decision_owner_priority_evidence_v1/"
    "priority_candidates.tsv"
)

OUTPUT_DIR = pathlib.Path(
    "/tmp/decision_owner_priority_semantic_classification_v1"
)

CLASSIFICATION_FILE = OUTPUT_DIR / "semantic_classification.tsv"
CONFIRMED_FILE = OUTPUT_DIR / "confirmed_candidates.tsv"
EXCLUDED_FILE = OUTPUT_DIR / "excluded_candidates.tsv"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved.tsv"


@dataclass(frozen=True, slots=True)
class Rule:
    stage: str
    path: str
    function: str
    classification: str
    reason: str
    owner_confirmed: int


RULES: tuple[Rule, ...] = (
    Rule(
        "STRATEGY",
        "src/finam_core/pipelines/paper_pipeline.py",
        "_on_quote_impl",
        "ORCHESTRATION_BOUNDARY",
        "coordinates strategy, regime, risk and execution; not a single-stage owner",
        0,
    ),
    Rule(
        "STRATEGY",
        "src/finam_core/execution/execution_dispatcher.py",
        "execute",
        "DOWNSTREAM_EXECUTION_GATE",
        "execution dispatcher consumes an already-created signal",
        0,
    ),

    Rule(
        "RISK",
        "src/finam_core/pipelines/paper_pipeline.py",
        "_on_quote_impl",
        "ORCHESTRATION_BOUNDARY",
        "invokes risk components but does not own centralized risk policy",
        0,
    ),
    Rule(
        "RISK",
        "src/finam_core/execution/execution_dispatcher.py",
        "execute",
        "DOWNSTREAM_EXECUTION_GATE",
        "execution-level validation is downstream from centralized risk",
        0,
    ),
    Rule(
        "RISK",
        "src/finam_core/risk/portfolio_risk_gate.py",
        "check",
        "CONFIRMED_DECISION_OWNER_CANDIDATE",
        "dedicated centralized portfolio risk gate returns authoritative risk decision",
        0,
    ),

    Rule(
        "RUNTIME",
        "src/finam_core/pipelines/paper_pipeline.py",
        "_on_quote_impl",
        "ORCHESTRATION_BOUNDARY",
        "aggregates runtime state but contains multiple unrelated decisions",
        0,
    ),
    Rule(
        "RUNTIME",
        "src/finam_core/pipelines/paper_pipeline.py",
        "_execute_br_signal_in_paper",
        "RUNTIME_GATE_CANDIDATE",
        "closest identified gate immediately before paper execution",
        0,
    ),

    Rule(
        "EXECUTION",
        "src/finam_core/pipelines/paper_pipeline.py",
        "_on_quote_impl",
        "ORCHESTRATION_BOUNDARY",
        "upstream orchestration is not the execution owner",
        0,
    ),
    Rule(
        "EXECUTION",
        "src/finam_core/adapters/grpc/orders_client.py",
        "place_limit_order",
        "BROKER_SIDE_EFFECT_BOUNDARY",
        "broker adapter performs external order submission",
        0,
    ),
    Rule(
        "EXECUTION",
        "src/finam_core/execution/execution_dispatcher.py",
        "place_limit_order",
        "CONFIRMED_DECISION_OWNER_CANDIDATE",
        "execution layer owns order construction and dispatch choice",
        0,
    ),
    Rule(
        "EXECUTION",
        "src/finam_core/execution/oco_order_manager.py",
        "_place_protection_orders",
        "PROTECTION_ORDER_SIDE_EFFECT",
        "manages downstream protective orders after entry decision",
        0,
    ),
    Rule(
        "EXECUTION",
        "src/finam_core/adapters/grpc/orders_client.py",
        "place_market_order",
        "BROKER_SIDE_EFFECT_BOUNDARY",
        "broker adapter performs external order submission",
        0,
    ),

    Rule(
        "BROKER",
        "src/finam_core/pipelines/paper_pipeline.py",
        "_on_quote_impl",
        "ORCHESTRATION_BOUNDARY",
        "does not own broker protocol or acknowledgement",
        0,
    ),
    Rule(
        "BROKER",
        "src/finam_core/adapters/grpc/orders_client.py",
        "place_limit_order",
        "CONFIRMED_DECISION_OWNER_CANDIDATE",
        "broker adapter owns gRPC request/response boundary for limit orders",
        0,
    ),
    Rule(
        "BROKER",
        "src/finam_core/adapters/grpc/orders_client.py",
        "place_market_order",
        "CONFIRMED_DECISION_OWNER_CANDIDATE",
        "broker adapter owns gRPC request/response boundary for market orders",
        0,
    ),
    Rule(
        "BROKER",
        "src/finam_core/execution/execution_dispatcher.py",
        "execute",
        "UPSTREAM_EXECUTION_GATE",
        "dispatcher selects execution path but does not own broker response",
        0,
    ),
    Rule(
        "BROKER",
        "src/finam_core/execution/execution_dispatcher.py",
        "place_limit_order",
        "UPSTREAM_EXECUTION_GATE",
        "execution dispatcher delegates to broker adapter",
        0,
    ),
    Rule(
        "BROKER",
        "src/finam_core/execution/oco_order_manager.py",
        "_place_protection_orders",
        "PROTECTION_ORDER_SIDE_EFFECT",
        "creates protective broker requests but is not broker authority",
        0,
    ),
)


def read_input() -> list[dict[str, str]]:
    if not INPUT.is_file():
        raise RuntimeError(f"input_missing:{INPUT}")

    with INPUT.open(
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
    rows: list[dict[str, object]],
) -> None:
    fields = (
        "stage",
        "path",
        "function",
        "line",
        "evidence_class",
        "semantic_classification",
        "reason",
        "owner_confirmed",
        "runtime_instrumentation",
    )

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

    source_rows = read_input()

    rule_index = {
        (
            rule.stage,
            rule.path,
            rule.function,
        ): rule
        for rule in RULES
    }

    classified: list[dict[str, object]] = []
    confirmed: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    unresolved: list[dict[str, object]] = []

    for raw in source_rows:
        key = (
            str(raw["stage"]),
            str(raw["path"]),
            str(raw["function"]),
        )

        rule = rule_index.get(key)

        if rule is None:
            row = {
                "stage": raw["stage"],
                "path": raw["path"],
                "function": raw["function"],
                "line": raw["line"],
                "evidence_class": raw["evidence_class"],
                "semantic_classification": "UNRESOLVED",
                "reason": "no_explicit_semantic_rule",
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
            unresolved.append(row)
            classified.append(row)
            continue

        row = {
            "stage": raw["stage"],
            "path": raw["path"],
            "function": raw["function"],
            "line": raw["line"],
            "evidence_class": raw["evidence_class"],
            "semantic_classification": rule.classification,
            "reason": rule.reason,
            "owner_confirmed": rule.owner_confirmed,
            "runtime_instrumentation": 0,
        }

        classified.append(row)

        if rule.classification == "CONFIRMED_DECISION_OWNER_CANDIDATE":
            confirmed.append(row)
        else:
            excluded.append(row)

    write_tsv(CLASSIFICATION_FILE, classified)
    write_tsv(CONFIRMED_FILE, confirmed)
    write_tsv(EXCLUDED_FILE, excluded)
    write_tsv(UNRESOLVED_FILE, unresolved)

    print(
        "=== AUDIT DECISION OWNER PRIORITY "
        "SEMANTIC CLASSIFICATION V1 ==="
    )
    print(f"input_count={len(source_rows)}")
    print(f"classified_count={len(classified)}")
    print(f"owner_candidate_count={len(confirmed)}")
    print(f"excluded_count={len(excluded)}")
    print(f"unresolved_count={len(unresolved)}")

    for row in classified:
        print(
            f"CLASSIFIED stage={row['stage']} "
            f"class={row['semantic_classification']} "
            f"path={row['path']} "
            f"function={row['function']} "
            f"owner_confirmed={row['owner_confirmed']}"
        )

    print(f"classification_file={CLASSIFICATION_FILE}")
    print(f"confirmed_file={CONFIRMED_FILE}")
    print(f"excluded_file={EXCLUDED_FILE}")
    print(f"unresolved_file={UNRESOLVED_FILE}")

    print("confirmed_owner_count=0")
    print("owner_assignment_performed=0")
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
        "DECISION_OWNER_PRIORITY_SEMANTIC_CLASSIFICATION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
