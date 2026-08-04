#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
from collections import defaultdict


SOURCE = pathlib.Path(
    "/tmp/strategy_owner_intent_points_v1/owner_candidates.tsv"
)

OUTPUT_DIR = pathlib.Path(
    "/tmp/strategy_owner_family_classification_v1"
)

CLASSIFIED_FILE = OUTPUT_DIR / "classified_candidates.tsv"
PRIMARY_FILE = OUTPUT_DIR / "primary_candidates.tsv"
LEGACY_FILE = OUTPUT_DIR / "legacy_candidates.tsv"
EXCLUDED_FILE = OUTPUT_DIR / "excluded_non_strategy.tsv"
SUMMARY_FILE = OUTPUT_DIR / "family_summary.tsv"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved.tsv"

ACTIVE_FAMILIES = {
    "BR",
    "NG",
    "EQUITY",
}

PIPELINE_PATH_MARKERS = (
    "/pipelines/",
)

NON_OWNER_CLASS_MARKERS = (
    "Regime",
    "Risk",
    "Guard",
    "Router",
    "Confidence",
    "Attribution",
    "Exit",
    "Profile",
)

NON_OWNER_FUNCTION_MARKERS = (
    "_process_",
    "_risk_",
    "_regime_",
    "_allows_",
    "_route_",
    "_execute_",
    "_persist_",
    "_save_",
    "_log_",
    "_audit_",
    "_reconcile_",
    "_self_heal_",
    "_build_exit_",
    "_position_intent_",
    "_apply_execution_",
    "_evaluate_take_profit",
    "_evaluate_trailing",
)

ACTIVE_OWNER_SYMBOLS = {
    "BR": {
        "BrConservativeBreakout.on_signal_bar",
    },
    "NG": {
        "NgConservativeBreakout.on_bars",
        "NgConservativeBreakoutM1.on_signal_bar",
        "NgVolatilityBreakout.on_bars",
        "NGIntradayStrategy.on_bar",
    },
    "EQUITY": {
        "VolatilityBreakoutEquity.on_quote",
        "MeanReversionEquity.on_quote",
    },
}

LEGACY_SYMBOL_MARKERS = (
    "SimpleMomentumStrategy",
    "SimpleMAStrategy",
    "SimpleReactiveStrategy",
    "MeanReversionStrategy",
    "BreakoutReactiveStrategy",
    "OnceBuyStrategy",
    "PrintStrategy",
    "VWAPBandsMRStrategy",
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


def classify(row: dict[str, str]) -> tuple[str, str]:
    family = row["family"]
    path = row["path"]
    class_name = row["class_name"]
    function = row["function"]
    symbol = row["qualified_name"]

    if any(marker in path for marker in PIPELINE_PATH_MARKERS):
        return "EXCLUDED_NON_STRATEGY", "PIPELINE_ORCHESTRATION"

    if any(marker in class_name for marker in NON_OWNER_CLASS_MARKERS):
        return "EXCLUDED_NON_STRATEGY", "GUARD_ROUTER_OR_POLICY_COMPONENT"

    if any(marker in function for marker in NON_OWNER_FUNCTION_MARKERS):
        return "EXCLUDED_NON_STRATEGY", "DOWNSTREAM_OR_SUPPORT_FUNCTION"

    if any(marker in symbol for marker in LEGACY_SYMBOL_MARKERS):
        return "LEGACY_STRATEGY", "LEGACY_OR_GENERIC_STRATEGY"

    if family not in ACTIVE_FAMILIES:
        return "LEGACY_OR_UNCLASSIFIED", "FAMILY_NOT_IN_ACTIVE_SCOPE"

    if symbol in ACTIVE_OWNER_SYMBOLS.get(family, set()):
        return "PRIMARY_FAMILY_CANDIDATE", "ACTIVE_STRATEGY_IMPLEMENTATION"

    if path.startswith("src/finam_core/strategy/"):
        return "SECONDARY_FAMILY_CANDIDATE", "STRATEGY_LAYER_CANDIDATE"

    return "UNRESOLVED", "CLASSIFICATION_RULE_NOT_MATCHED"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source_rows = read_rows()

    classified: list[dict[str, object]] = []
    primary: list[dict[str, object]] = []
    legacy: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    unresolved: list[dict[str, object]] = []

    for row in source_rows:
        classification, reason = classify(row)

        result = {
            "family": row["family"],
            "path": row["path"],
            "class_name": row["class_name"],
            "function": row["function"],
            "qualified_name": row["qualified_name"],
            "line": row["line"],
            "score": row["score"],
            "constructor_count": row["constructor_count"],
            "positive_signal_return_count": row[
                "positive_signal_return_count"
            ],
            "absence_return_count": row["absence_return_count"],
            "direction_assignment_count": row[
                "direction_assignment_count"
            ],
            "classification": classification,
            "reason": reason,
            "owner_confirmed": 0,
            "runtime_instrumentation": 0,
        }

        classified.append(result)

        if classification == "PRIMARY_FAMILY_CANDIDATE":
            primary.append(result)
        elif classification in {
            "LEGACY_STRATEGY",
            "LEGACY_OR_UNCLASSIFIED",
        }:
            legacy.append(result)
        elif classification == "EXCLUDED_NON_STRATEGY":
            excluded.append(result)
        elif classification == "UNRESOLVED":
            unresolved.append(
                {
                    "family": row["family"],
                    "path": row["path"],
                    "symbol": row["qualified_name"],
                    "reason": reason,
                }
            )

    family_index: dict[str, list[dict[str, object]]] = defaultdict(list)

    for row in primary:
        family_index[str(row["family"])].append(row)

    summary: list[dict[str, object]] = []

    for family in sorted(ACTIVE_FAMILIES):
        rows = family_index.get(family, [])

        summary.append(
            {
                "family": family,
                "primary_candidate_count": len(rows),
                "primary_symbols": ",".join(
                    str(row["qualified_name"])
                    for row in rows
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

        if not rows:
            unresolved.append(
                {
                    "family": family,
                    "path": "",
                    "symbol": "",
                    "reason": "NO_PRIMARY_FAMILY_CANDIDATE",
                }
            )

    fields = (
        "family",
        "path",
        "class_name",
        "function",
        "qualified_name",
        "line",
        "score",
        "constructor_count",
        "positive_signal_return_count",
        "absence_return_count",
        "direction_assignment_count",
        "classification",
        "reason",
        "owner_confirmed",
        "runtime_instrumentation",
    )

    write_tsv(CLASSIFIED_FILE, fields, classified)
    write_tsv(PRIMARY_FILE, fields, primary)
    write_tsv(LEGACY_FILE, fields, legacy)
    write_tsv(EXCLUDED_FILE, fields, excluded)

    write_tsv(
        SUMMARY_FILE,
        (
            "family",
            "primary_candidate_count",
            "primary_symbols",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        summary,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "family",
            "path",
            "symbol",
            "reason",
        ),
        unresolved,
    )

    print("=== BUILD STRATEGY OWNER FAMILY CLASSIFICATION V1 ===")
    print(f"input_candidate_count={len(source_rows)}")
    print(f"primary_candidate_count={len(primary)}")
    print(f"legacy_candidate_count={len(legacy)}")
    print(f"excluded_non_strategy_count={len(excluded)}")
    print(f"unresolved_count={len(unresolved)}")

    for row in summary:
        print(
            f"FAMILY name={row['family']} "
            f"primary_count={row['primary_candidate_count']} "
            f"symbols={row['primary_symbols']}"
        )

    for row in primary:
        print(
            f"PRIMARY_CANDIDATE family={row['family']} "
            f"symbol={row['qualified_name']} "
            f"path={row['path']} "
            f"score={row['score']}"
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
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "STRATEGY_OWNER_FAMILY_CLASSIFICATION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
