#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
from collections import defaultdict


SOURCE = pathlib.Path(
    "/tmp/regime_owner_candidates_v1/owner_candidates.tsv"
)

OUTPUT_DIR = pathlib.Path(
    "/tmp/regime_semantic_classification_v1"
)

CLASSIFICATION_FILE = OUTPUT_DIR / "semantic_classification.tsv"
CLASSIFIER_FILE = OUTPUT_DIR / "classifier_candidates.tsv"
FAMILY_FILE = OUTPUT_DIR / "family_specific_candidates.tsv"
CONSUMERS_FILE = OUTPUT_DIR / "consumers_and_gates.tsv"
RESEARCH_FILE = OUTPUT_DIR / "research_only_candidates.tsv"
INITIALIZERS_FILE = OUTPUT_DIR / "excluded_initializers.tsv"
SUMMARY_FILE = OUTPUT_DIR / "family_summary.tsv"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved.tsv"

CLASSIFIER_PATH_PREFIXES = (
    "src/finam_core/regime/",
    "src/finam_core/domain/regime/",
    "src/finam_core/alpha/regime_",
)

FAMILY_CLASSIFIER_SYMBOLS = {
    "BRRegimeLayer.evaluate",
}

GENERIC_CLASSIFIER_SYMBOLS = {
    "RegimeEngine.evaluate",
    "RegimeLabeler.label",
    "RegimeDetector.detect",
    "RegimeLayerV2.classify",
    "CandleRegimeEngineV2.classify",
}

RESEARCH_PATH_MARKERS = (
    "/research/",
    "/analytics/",
)

CONSUMER_PATH_MARKERS = (
    "/pipelines/",
    "/execution/",
    "/risk/",
    "/runtime/",
    "/policy/",
    "/governance/",
    "/exits/",
)

CONSUMER_CLASS_MARKERS = (
    "Filter",
    "Gate",
    "Policy",
    "Decision",
    "Control",
    "Override",
    "Modifier",
    "Selector",
)

CONSUMER_FUNCTION_MARKERS = (
    "allow",
    "allows",
    "decide",
    "select",
    "resolve_regime_strategy",
    "build_regime_runtime",
    "build_regime_matrix",
    "_regime_policy_",
    "_regime_allows_",
    "_adaptive_regime_filter",
    "_market_shock_gate",
)

CLASSIFIER_FUNCTION_MARKERS = (
    "classify",
    "detect",
    "label",
    "calculate",
    "infer",
)

INITIALIZER_FUNCTIONS = {
    "__init__",
}

STRATEGY_INTERNAL_SYMBOLS = {
    "BrConservativeBreakout.on_regime_bar",
    "VolatilityBreakoutEquity.on_quote",
}

FIELDS = (
    "family",
    "path",
    "class_name",
    "function",
    "qualified_name",
    "line",
    "constructor_count",
    "regime_assignment_count",
    "regime_return_count",
    "absence_return_count",
    "regime_call_count",
    "function_name_marker_count",
    "class_name_marker_count",
    "side_effect_count",
    "score",
    "source_classification",
    "semantic_classification",
    "reason",
    "owner_confirmed",
    "runtime_instrumentation",
)


def read_rows() -> list[dict[str, str]]:
    if not SOURCE.is_file():
        raise RuntimeError(f"source_missing:{SOURCE}")

    with SOURCE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


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


def classify(row: dict[str, str]) -> tuple[str, str]:
    path = row["path"]
    class_name = row["class_name"]
    function = row["function"]
    symbol = row["qualified_name"]

    function_lower = function.lower()

    if function in INITIALIZER_FUNCTIONS:
        return (
            "EXCLUDED_INITIALIZER",
            "INITIALIZATION_NOT_REGIME_DECISION",
        )

    if symbol in STRATEGY_INTERNAL_SYMBOLS:
        return (
            "STRATEGY_INTERNAL_REGIME_STATE",
            "STRATEGY_CONSUMES_OR_UPDATES_REGIME_CONTEXT",
        )

    if symbol in FAMILY_CLASSIFIER_SYMBOLS:
        return (
            "FAMILY_REGIME_CLASSIFIER_CANDIDATE",
            "EXPLICIT_FAMILY_REGIME_CLASSIFICATION",
        )

    if symbol in GENERIC_CLASSIFIER_SYMBOLS:
        return (
            "GENERIC_REGIME_CLASSIFIER_CANDIDATE",
            "EXPLICIT_GENERIC_REGIME_CLASSIFICATION",
        )

    if any(marker in path for marker in RESEARCH_PATH_MARKERS):
        return (
            "RESEARCH_ONLY_REGIME_ENGINE",
            "RESEARCH_OR_ANALYTICS_SCOPE",
        )

    if (
        path.startswith(CLASSIFIER_PATH_PREFIXES)
        and any(
            marker in function_lower
            for marker in CLASSIFIER_FUNCTION_MARKERS
        )
    ):
        return (
            "GENERIC_REGIME_CLASSIFIER_CANDIDATE",
            "REGIME_LAYER_CLASSIFICATION_METHOD",
        )

    if (
        any(marker in path for marker in CONSUMER_PATH_MARKERS)
        or any(marker in class_name for marker in CONSUMER_CLASS_MARKERS)
        or any(marker in function_lower for marker in CONSUMER_FUNCTION_MARKERS)
    ):
        return (
            "REGIME_CONSUMER_OR_GATE",
            "CONSUMES_REGIME_FOR_POLICY_OR_GATE",
        )

    if (
        any(marker in function_lower for marker in CLASSIFIER_FUNCTION_MARKERS)
        and int(row["regime_return_count"]) > 0
    ):
        return (
            "REVIEW_CLASSIFIER_CANDIDATE",
            "CLASSIFICATION_SEMANTICS_REQUIRE_RUNTIME_REVIEW",
        )

    return (
        "NON_OWNER_REGIME_CONTEXT",
        "REGIME_DATA_OR_CONTEXT_WITHOUT_OWNER_PROOF",
    )


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source_rows = read_rows()

    classified: list[dict[str, object]] = []
    classifiers: list[dict[str, object]] = []
    family_specific: list[dict[str, object]] = []
    consumers: list[dict[str, object]] = []
    research: list[dict[str, object]] = []
    initializers: list[dict[str, object]] = []
    unresolved: list[dict[str, object]] = []

    for row in source_rows:
        semantic_classification, reason = classify(row)

        result = {
            "family": row["family"],
            "path": row["path"],
            "class_name": row["class_name"],
            "function": row["function"],
            "qualified_name": row["qualified_name"],
            "line": row["line"],
            "constructor_count": row["constructor_count"],
            "regime_assignment_count": row["regime_assignment_count"],
            "regime_return_count": row["regime_return_count"],
            "absence_return_count": row["absence_return_count"],
            "regime_call_count": row["regime_call_count"],
            "function_name_marker_count": row["function_name_marker_count"],
            "class_name_marker_count": row["class_name_marker_count"],
            "side_effect_count": row["side_effect_count"],
            "score": row["score"],
            "source_classification": row["classification"],
            "semantic_classification": semantic_classification,
            "reason": reason,
            "owner_confirmed": 0,
            "runtime_instrumentation": 0,
        }

        classified.append(result)

        if semantic_classification in {
            "GENERIC_REGIME_CLASSIFIER_CANDIDATE",
            "REVIEW_CLASSIFIER_CANDIDATE",
        }:
            classifiers.append(result)
        elif semantic_classification == "FAMILY_REGIME_CLASSIFIER_CANDIDATE":
            family_specific.append(result)
        elif semantic_classification == "REGIME_CONSUMER_OR_GATE":
            consumers.append(result)
        elif semantic_classification == "RESEARCH_ONLY_REGIME_ENGINE":
            research.append(result)
        elif semantic_classification == "EXCLUDED_INITIALIZER":
            initializers.append(result)

    classifier_symbols = {
        str(row["qualified_name"])
        for row in classifiers
    }

    required_symbols = {
        "RegimeEngine.evaluate",
        "RegimeLabeler.label",
        "RegimeDetector.detect",
        "RegimeLayerV2.classify",
    }

    for symbol in sorted(required_symbols - classifier_symbols):
        unresolved.append(
            {
                "family": "GENERIC",
                "path": "",
                "class_name": "",
                "function": "",
                "qualified_name": symbol,
                "line": "",
                "constructor_count": "0",
                "regime_assignment_count": "0",
                "regime_return_count": "0",
                "absence_return_count": "0",
                "regime_call_count": "0",
                "function_name_marker_count": "0",
                "class_name_marker_count": "0",
                "side_effect_count": "0",
                "score": "0",
                "source_classification": "",
                "semantic_classification": "UNRESOLVED",
                "reason": "EXPECTED_CLASSIFIER_NOT_DISCOVERED",
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    family_index: dict[str, list[dict[str, object]]] = defaultdict(list)

    for row in classified:
        family_index[str(row["family"])].append(row)

    summary: list[dict[str, object]] = []

    for family in ("BR", "NG", "EQUITY", "GENERIC"):
        rows = family_index.get(family, [])

        summary.append(
            {
                "family": family,
                "path": "",
                "class_name": "",
                "function": "",
                "qualified_name": "",
                "line": "",
                "constructor_count": "0",
                "regime_assignment_count": "0",
                "regime_return_count": "0",
                "absence_return_count": "0",
                "regime_call_count": "0",
                "function_name_marker_count": "0",
                "class_name_marker_count": "0",
                "side_effect_count": "0",
                "score": "0",
                "source_classification": "",
                "semantic_classification": "FAMILY_SUMMARY",
                "reason": (
                    f"total={len(rows)};"
                    f"classifiers={sum(r['semantic_classification'] in {'GENERIC_REGIME_CLASSIFIER_CANDIDATE', 'FAMILY_REGIME_CLASSIFIER_CANDIDATE', 'REVIEW_CLASSIFIER_CANDIDATE'} for r in rows)};"
                    f"consumers={sum(r['semantic_classification'] == 'REGIME_CONSUMER_OR_GATE' for r in rows)}"
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    write_tsv(CLASSIFICATION_FILE, classified)
    write_tsv(CLASSIFIER_FILE, classifiers)
    write_tsv(FAMILY_FILE, family_specific)
    write_tsv(CONSUMERS_FILE, consumers)
    write_tsv(RESEARCH_FILE, research)
    write_tsv(INITIALIZERS_FILE, initializers)
    write_tsv(SUMMARY_FILE, summary)
    write_tsv(UNRESOLVED_FILE, unresolved)

    print("=== BUILD REGIME SEMANTIC CLASSIFICATION V1 ===")
    print(f"input_candidate_count={len(source_rows)}")
    print(f"generic_classifier_candidate_count={len(classifiers)}")
    print(f"family_classifier_candidate_count={len(family_specific)}")
    print(f"consumer_or_gate_count={len(consumers)}")
    print(f"research_only_count={len(research)}")
    print(f"initializer_count={len(initializers)}")
    print(f"unresolved_count={len(unresolved)}")

    for row in classifiers:
        print(
            f"CLASSIFIER class={row['semantic_classification']} "
            f"family={row['family']} "
            f"symbol={row['qualified_name']} "
            f"path={row['path']}"
        )

    for row in family_specific:
        print(
            f"FAMILY_CLASSIFIER family={row['family']} "
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
    print("VERDICT=REGIME_SEMANTIC_CLASSIFICATION_V1_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
