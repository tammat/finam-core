#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib


SOURCE = pathlib.Path(
    "/tmp/edge_owner_candidates_v1/owner_candidates.tsv"
)

OUT = pathlib.Path(
    "/tmp/edge_semantic_classification_v1"
)

CLASSIFICATION_FILE = OUT / "semantic_classification.tsv"
AUTHORITATIVE_FILE = OUT / "authoritative_decision_candidates.tsv"
VALIDATION_FILE = OUT / "validation_engines.tsv"
METRICS_FILE = OUT / "metric_calculators.tsv"
PROMOTION_FILE = OUT / "promotion_and_ranking.tsv"
RUNTIME_FILE = OUT / "runtime_guards.tsv"
RESEARCH_FILE = OUT / "research_only.tsv"
EXCLUDED_FILE = OUT / "excluded_candidates.tsv"
SUMMARY_FILE = OUT / "summary.tsv"
UNRESOLVED_FILE = OUT / "unresolved.tsv"

FIELDS = (
    "scope",
    "path",
    "class_name",
    "function",
    "qualified_name",
    "line",
    "score",
    "source_classification",
    "semantic_classification",
    "reason",
    "owner_confirmed",
    "runtime_instrumentation",
)

AUTHORITATIVE_IDENTITIES = {
    (
        "src/finam_core/analytics/directional_edge_guard.py",
        "DirectionalEdgeGuard.decide",
    ),
    (
        "src/finam_core/analytics/statistical_validation_decision.py",
        "StatisticalValidationDecisionEngine.decide",
    ),
    (
        "src/finam_core/analytics/session_edge_guard.py",
        "SessionEdgeGuard.decide",
    ),
}

RISK_SESSION_EDGE_IDENTITY = (
    "src/finam_core/risk/session_edge_guard.py",
    "SessionEdgeGuard.decide",
)

VALIDATION_SYMBOLS = {
    "EdgeValidationEngine.validate",
    "StatisticalValidationEngine.validate",
    "evaluate_walk_forward",
    "parameter_plateau_check",
    "candidate_statistical_gate",
    "negative_control_check",
}

METRIC_SYMBOLS = {
    "StrategyScorecardCalculator.calculate",
    "calculate_trade_statistics",
    "calculate_strategy_statistics_v2",
    "build_edge_stats",
    "build_edge_bucket",
    "aggregate_edge_by_profile",
}

PROMOTION_SYMBOLS = {
    "promotion_decision",
    "StrategyRanker.rank",
    "calculate_strategy_rank_v2",
    "ExitPolicySelector.select_best_policy",
    "evaluate_active_paper_champion",
    "evaluate_paper_challenger",
}

RUNTIME_SYMBOLS = {
    "EdgeGatePnlDecayMonitorV1.evaluate",
    "RuntimeGuardSoftBlockModeV1.apply",
    "RuntimeGuardDecisionAdapterV1.evaluate",
    "RuntimeShadowObservationV1.evaluate",
    "decide_monday_paper_entry_gate_v1",
    "decide_market_context_admission_v1",
}

RESEARCH_PATH_MARKERS = (
    "/research/",
    "/experiments/",
)

SUPPORT_FUNCTION_MARKERS = (
    "__init__",
    "_make_key",
    "_load_",
    "save",
    "migrate",
    "build_equity_curve",
    "reconstruct",
)


def read_rows() -> list[dict[str, str]]:
    if not SOURCE.is_file():
        raise RuntimeError(
            f"source_file_missing:{SOURCE}"
        )

    with SOURCE.open(
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
    rows: list[dict[str, object]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=FIELDS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def classify(
    row: dict[str, str],
) -> tuple[str, str]:
    symbol = row["qualified_name"]
    path = row["path"]
    function = row["function"]

    identity = (path, symbol)

    if identity in AUTHORITATIVE_IDENTITIES:
        return (
            "AUTHORITATIVE_EDGE_DECISION_CANDIDATE",
            "EXPLICIT_EDGE_ALLOW_REJECT_DECISION",
        )

    if identity == RISK_SESSION_EDGE_IDENTITY:
        return (
            "EDGE_RISK_CONSUMER",
            "RISK_LAYER_CONSUMES_SESSION_EDGE_DECISION",
        )

    if symbol in VALIDATION_SYMBOLS:
        return (
            "EDGE_VALIDATION_ENGINE",
            "VALIDATES_EDGE_EVIDENCE_OR_ROBUSTNESS",
        )

    if symbol in METRIC_SYMBOLS:
        return (
            "EDGE_METRIC_CALCULATOR",
            "CALCULATES_EDGE_METRICS_WITHOUT_AUTHORITY",
        )

    if symbol in PROMOTION_SYMBOLS:
        return (
            "EDGE_PROMOTION_OR_RANKING",
            "RANKS_OR_PROMOTES_CANDIDATES",
        )

    if symbol in RUNTIME_SYMBOLS:
        return (
            "EDGE_RUNTIME_GUARD",
            "APPLIES_RUNTIME_OR_SHADOW_EDGE_POLICY",
        )

    if any(
        marker in path
        for marker in RESEARCH_PATH_MARKERS
    ):
        return (
            "RESEARCH_ONLY_EDGE_COMPONENT",
            "RESEARCH_SCOPE_NOT_RUNTIME_AUTHORITY",
        )

    if any(
        marker in function
        for marker in SUPPORT_FUNCTION_MARKERS
    ):
        return (
            "EXCLUDED_SUPPORT_FUNCTION",
            "SUPPORT_OR_PERSISTENCE_FUNCTION",
        )

    if row["scope"] == "ANALYTICS":
        if int(row["decision_return_count"] or 0) > 0:
            return (
                "REVIEW_EDGE_DECISION_CANDIDATE",
                "DECISION_SEMANTICS_REQUIRE_BOUNDARY_REVIEW",
            )

        return (
            "ANALYTICS_EDGE_COMPONENT",
            "ANALYTICS_WITHOUT_AUTHORITATIVE_DECISION_PROOF",
        )

    if row["scope"] == "RUNTIME":
        return (
            "EDGE_RUNTIME_CONSUMER",
            "RUNTIME_CONSUMES_EDGE_STATE",
        )

    if row["scope"] == "RISK":
        return (
            "EDGE_RISK_CONSUMER",
            "RISK_CONSUMES_EDGE_EVIDENCE",
        )

    if row["scope"] == "STRATEGY":
        return (
            "STRATEGY_EDGE_CONSUMER",
            "STRATEGY_USES_EDGE_CONTEXT",
        )

    return (
        "NON_AUTHORITATIVE_EDGE_COMPONENT",
        "NO_AUTHORITATIVE_EDGE_DECISION_PROOF",
    )


def main() -> int:
    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_rows = read_rows()

    classified: list[dict[str, object]] = []
    authoritative: list[dict[str, object]] = []
    validation: list[dict[str, object]] = []
    metrics: list[dict[str, object]] = []
    promotion: list[dict[str, object]] = []
    runtime: list[dict[str, object]] = []
    research: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    unresolved: list[dict[str, object]] = []

    for row in source_rows:
        semantic_classification, reason = classify(
            row
        )

        result = {
            "scope": row["scope"],
            "path": row["path"],
            "class_name": row["class_name"],
            "function": row["function"],
            "qualified_name": row[
                "qualified_name"
            ],
            "line": row["line"],
            "score": row["score"],
            "source_classification": row[
                "classification"
            ],
            "semantic_classification": (
                semantic_classification
            ),
            "reason": reason,
            "owner_confirmed": 0,
            "runtime_instrumentation": 0,
        }

        classified.append(result)

        if semantic_classification in {
            "AUTHORITATIVE_EDGE_DECISION_CANDIDATE",
            "REVIEW_EDGE_DECISION_CANDIDATE",
        }:
            authoritative.append(result)
        elif semantic_classification == (
            "EDGE_VALIDATION_ENGINE"
        ):
            validation.append(result)
        elif semantic_classification == (
            "EDGE_METRIC_CALCULATOR"
        ):
            metrics.append(result)
        elif semantic_classification == (
            "EDGE_PROMOTION_OR_RANKING"
        ):
            promotion.append(result)
        elif semantic_classification in {
            "EDGE_RUNTIME_GUARD",
            "EDGE_RUNTIME_CONSUMER",
        }:
            runtime.append(result)
        elif semantic_classification == (
            "RESEARCH_ONLY_EDGE_COMPONENT"
        ):
            research.append(result)
        elif semantic_classification == (
            "EXCLUDED_SUPPORT_FUNCTION"
        ):
            excluded.append(result)

    authoritative_symbols = {
        str(row["qualified_name"])
        for row in authoritative
    }

    authoritative_identities = {
        (
            str(row["path"]),
            str(row["qualified_name"]),
        )
        for row in authoritative
        if row["semantic_classification"]
        == "AUTHORITATIVE_EDGE_DECISION_CANDIDATE"
    }

    for expected_path, symbol in sorted(
        AUTHORITATIVE_IDENTITIES
        - authoritative_identities
    ):
        unresolved.append(
            {
                "scope": "EDGE",
                "path": expected_path,
                "class_name": "",
                "function": "",
                "qualified_name": symbol,
                "line": "",
                "score": "0",
                "source_classification": "",
                "semantic_classification": (
                    "UNRESOLVED"
                ),
                "reason": (
                    "EXPECTED_DECISION_CANDIDATE_MISSING"
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    summary_rows: list[dict[str, object]] = []

    classes = (
        "AUTHORITATIVE_EDGE_DECISION_CANDIDATE",
        "REVIEW_EDGE_DECISION_CANDIDATE",
        "EDGE_VALIDATION_ENGINE",
        "EDGE_METRIC_CALCULATOR",
        "EDGE_PROMOTION_OR_RANKING",
        "EDGE_RUNTIME_GUARD",
        "EDGE_RUNTIME_CONSUMER",
        "EDGE_RISK_CONSUMER",
        "STRATEGY_EDGE_CONSUMER",
        "RESEARCH_ONLY_EDGE_COMPONENT",
        "ANALYTICS_EDGE_COMPONENT",
        "EXCLUDED_SUPPORT_FUNCTION",
        "NON_AUTHORITATIVE_EDGE_COMPONENT",
    )

    for class_name in classes:
        count = sum(
            row["semantic_classification"]
            == class_name
            for row in classified
        )

        summary_rows.append(
            {
                "scope": "SUMMARY",
                "path": "",
                "class_name": "",
                "function": "",
                "qualified_name": "",
                "line": "",
                "score": str(count),
                "source_classification": "",
                "semantic_classification": (
                    class_name
                ),
                "reason": f"count={count}",
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    write_tsv(
        CLASSIFICATION_FILE,
        classified,
    )
    write_tsv(
        AUTHORITATIVE_FILE,
        authoritative,
    )
    write_tsv(
        VALIDATION_FILE,
        validation,
    )
    write_tsv(
        METRICS_FILE,
        metrics,
    )
    write_tsv(
        PROMOTION_FILE,
        promotion,
    )
    write_tsv(
        RUNTIME_FILE,
        runtime,
    )
    write_tsv(
        RESEARCH_FILE,
        research,
    )
    write_tsv(
        EXCLUDED_FILE,
        excluded,
    )
    write_tsv(
        SUMMARY_FILE,
        summary_rows,
    )
    write_tsv(
        UNRESOLVED_FILE,
        unresolved,
    )

    confirmed_candidates = [
        row
        for row in authoritative
        if row["semantic_classification"]
        == "AUTHORITATIVE_EDGE_DECISION_CANDIDATE"
    ]

    review_candidates = [
        row
        for row in authoritative
        if row["semantic_classification"]
        == "REVIEW_EDGE_DECISION_CANDIDATE"
    ]

    print(
        "=== BUILD EDGE SEMANTIC "
        "CLASSIFICATION V1 ==="
    )
    print(
        f"input_candidate_count="
        f"{len(source_rows)}"
    )
    print(
        f"authoritative_candidate_count="
        f"{len(confirmed_candidates)}"
    )
    print(
        f"review_decision_candidate_count="
        f"{len(review_candidates)}"
    )
    print(
        f"validation_engine_count="
        f"{len(validation)}"
    )
    print(
        f"metric_calculator_count="
        f"{len(metrics)}"
    )
    print(
        f"promotion_or_ranking_count="
        f"{len(promotion)}"
    )
    print(
        f"runtime_guard_count="
        f"{len(runtime)}"
    )
    print(
        f"research_only_count="
        f"{len(research)}"
    )
    print(
        f"unresolved_count="
        f"{len(unresolved)}"
    )

    for row in authoritative:
        print(
            "EDGE_DECISION_CANDIDATE "
            f"class="
            f"{row['semantic_classification']} "
            f"symbol={row['qualified_name']} "
            f"path={row['path']}"
        )

    print("confirmed_owner_count=0")
    print("owner_assignment_performed=0")
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
        "EDGE_SEMANTIC_CLASSIFICATION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
