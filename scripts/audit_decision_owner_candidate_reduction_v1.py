#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
import subprocess
from collections import Counter
from dataclasses import dataclass


ROOT = pathlib.Path("/opt/finam-core").resolve()

INSTRUMENTATION_SCRIPT = (
    ROOT
    / "scripts"
    / "audit_decision_funnel_instrumentation_plan_v1.py"
)

INSTRUMENTATION_DIR = pathlib.Path(
    "/tmp/decision_funnel_instrumentation_plan_v1"
)
INPUT_POINTS = INSTRUMENTATION_DIR / "instrumentation_points.tsv"

OUTPUT_DIR = pathlib.Path(
    "/tmp/decision_owner_candidate_reduction_v1"
)
REDUCED_FILE = OUTPUT_DIR / "reduced_candidates.tsv"
EXCLUDED_FILE = OUTPUT_DIR / "excluded_candidates.tsv"
SUMMARY_FILE = OUTPUT_DIR / "stage_summary.tsv"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved_stages.tsv"

STAGES = (
    "MARKET_DATA",
    "STRATEGY",
    "REGIME",
    "EDGE",
    "RISK",
    "PORTFOLIO",
    "RUNTIME",
    "EXECUTION",
    "BROKER",
    "FILL",
)

# На первом этапе оставляем не более 15 кандидатов на стадию.
MAX_CANDIDATES_PER_STAGE = 15

READ_MODEL_PREFIXES = (
    "src/marketcore/api/",
    "src/marketcore/presentation/",
)

READ_MODEL_MARKERS = (
    "/renderer/",
    "/resolver/",
    "/viewmodel/",
    "/pages/",
    "/read_models/",
    "serve_knowledge_graph_api",
    "control_center",
)

ANALYTICS_PREFIXES = (
    "src/scripts/analytics/",
    "src/scripts/research/",
)

SCRIPT_PREFIXES = (
    "src/scripts/",
    "scripts/",
)

TEST_TOOLING_MARKERS = (
    "/tests/",
    "test_",
    "audit_",
    "validate_",
    "apply_",
    "repair_",
    "patch_",
)

# Product namespaces, где потенциально могут находиться реальные
# владельцы торговых решений.
PRODUCT_OWNER_PREFIXES = (
    "src/finam_core/pipelines/",
    "src/finam_core/strategy/",
    "src/finam_core/regime/",
    "src/finam_core/risk/",
    "src/finam_core/portfolio/",
    "src/finam_core/runtime/",
    "src/finam_core/execution/",
    "src/finam_core/adapters/",
)


@dataclass(frozen=True, slots=True)
class Candidate:
    stage: str
    rank: int
    score: int
    path: str
    function: str
    line: int
    source_classification: str
    stage_markers: str
    decision_markers: str
    mutation_calls: str
    tracked_references: int


def ensure_instrumentation_output() -> None:
    if INPUT_POINTS.is_file():
        return

    if not INSTRUMENTATION_SCRIPT.is_file():
        raise RuntimeError(
            f"instrumentation_script_missing:"
            f"{INSTRUMENTATION_SCRIPT}"
        )

    result = subprocess.run(
        [
            str(ROOT / "venv/bin/python"),
            str(INSTRUMENTATION_SCRIPT),
        ],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    print(result.stdout, end="")

    if result.returncode != 0:
        raise RuntimeError(
            f"instrumentation_audit_failed:"
            f"{result.returncode}"
        )

    if not INPUT_POINTS.is_file():
        raise RuntimeError(
            f"instrumentation_points_missing:"
            f"{INPUT_POINTS}"
        )


def read_candidates() -> list[Candidate]:
    rows: list[Candidate] = []

    with INPUT_POINTS.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        reader = csv.DictReader(
            stream,
            delimiter="\t",
        )

        required = {
            "stage",
            "rank",
            "score",
            "path",
            "function",
            "line",
            "classification",
            "stage_markers",
            "decision_markers",
            "mutation_calls",
            "tracked_references",
        }

        actual = set(reader.fieldnames or ())

        missing = required - actual

        if missing:
            raise RuntimeError(
                "instrumentation_columns_missing:"
                + ",".join(sorted(missing))
            )

        for raw in reader:
            stage = str(raw["stage"]).strip()

            if stage not in STAGES:
                continue

            rows.append(
                Candidate(
                    stage=stage,
                    rank=int(raw["rank"]),
                    score=int(raw["score"]),
                    path=str(raw["path"]).strip(),
                    function=str(raw["function"]).strip(),
                    line=int(raw["line"]),
                    source_classification=str(
                        raw["classification"]
                    ).strip(),
                    stage_markers=str(
                        raw["stage_markers"]
                    ).strip(),
                    decision_markers=str(
                        raw["decision_markers"]
                    ).strip(),
                    mutation_calls=str(
                        raw["mutation_calls"]
                    ).strip(),
                    tracked_references=int(
                        raw["tracked_references"]
                    ),
                )
            )

    return rows


def classify_path(
    candidate: Candidate,
) -> tuple[str, str]:
    path_lower = candidate.path.lower()
    function_lower = candidate.function.lower()

    if (
        candidate.path.startswith(READ_MODEL_PREFIXES)
        or any(
            marker in path_lower
            for marker in READ_MODEL_MARKERS
        )
    ):
        return (
            "READ_MODEL_ONLY",
            "api_presentation_resolver_renderer_or_read_model",
        )

    if candidate.path.startswith(ANALYTICS_PREFIXES):
        return (
            "ANALYTICS_ONLY",
            "offline_analytics_or_research_script",
        )

    if (
        candidate.path.startswith(SCRIPT_PREFIXES)
        and not candidate.path.startswith(
            PRODUCT_OWNER_PREFIXES
        )
    ):
        return (
            "SCRIPT_ORCHESTRATOR",
            "standalone_script_not_runtime_owner",
        )

    if any(
        marker in path_lower
        or marker in function_lower
        for marker in TEST_TOOLING_MARKERS
    ):
        return (
            "TEST_OR_TOOLING",
            "test_audit_validation_or_patch_tool",
        )

    if candidate.path.startswith(PRODUCT_OWNER_PREFIXES):
        return (
            "CANDIDATE_FOR_MANUAL_REVIEW",
            "product_runtime_namespace",
        )

    return (
        "UNRESOLVED",
        "namespace_not_proven",
    )


def write_tsv(
    path: pathlib.Path,
    fieldnames: tuple[str, ...],
    rows: list[dict[str, object]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    ensure_instrumentation_output()
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidates = read_candidates()

    reduced: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    unresolved: list[dict[str, object]] = []

    stage_input_count = Counter()
    stage_review_count = Counter()
    stage_excluded_count = Counter()
    stage_unresolved_count = Counter()

    for candidate in candidates:
        stage_input_count[candidate.stage] += 1

        classification, reason = classify_path(candidate)

        row: dict[str, object] = {
            "stage": candidate.stage,
            "source_rank": candidate.rank,
            "score": candidate.score,
            "path": candidate.path,
            "function": candidate.function,
            "line": candidate.line,
            "classification": classification,
            "reason": reason,
            "source_classification": (
                candidate.source_classification
            ),
            "stage_markers": candidate.stage_markers,
            "decision_markers": (
                candidate.decision_markers
            ),
            "mutation_calls": candidate.mutation_calls,
            "tracked_references": (
                candidate.tracked_references
            ),
            "owner_confirmed": 0,
            "runtime_instrumentation": 0,
        }

        if classification == "CANDIDATE_FOR_MANUAL_REVIEW":
            if (
                stage_review_count[candidate.stage]
                < MAX_CANDIDATES_PER_STAGE
            ):
                reduced.append(row)
                stage_review_count[candidate.stage] += 1
            else:
                row["classification"] = (
                    "EXCLUDED_BY_STAGE_LIMIT"
                )
                row["reason"] = (
                    "candidate_rank_below_manual_review_limit"
                )
                excluded.append(row)
                stage_excluded_count[candidate.stage] += 1

        elif classification == "UNRESOLVED":
            unresolved.append(row)
            stage_unresolved_count[candidate.stage] += 1

        else:
            excluded.append(row)
            stage_excluded_count[candidate.stage] += 1

    # Стабильная сортировка: стадия, score, путь, строка.
    stage_index = {
        stage: index
        for index, stage in enumerate(STAGES)
    }

    reduced.sort(
        key=lambda row: (
            stage_index[str(row["stage"])],
            -int(row["score"]),
            str(row["path"]),
            int(row["line"]),
        )
    )

    excluded.sort(
        key=lambda row: (
            stage_index[str(row["stage"])],
            str(row["classification"]),
            -int(row["score"]),
            str(row["path"]),
            int(row["line"]),
        )
    )

    unresolved.sort(
        key=lambda row: (
            stage_index[str(row["stage"])],
            -int(row["score"]),
            str(row["path"]),
            int(row["line"]),
        )
    )

    fields = (
        "stage",
        "source_rank",
        "score",
        "path",
        "function",
        "line",
        "classification",
        "reason",
        "source_classification",
        "stage_markers",
        "decision_markers",
        "mutation_calls",
        "tracked_references",
        "owner_confirmed",
        "runtime_instrumentation",
    )

    write_tsv(
        REDUCED_FILE,
        fields,
        reduced,
    )
    write_tsv(
        EXCLUDED_FILE,
        fields,
        excluded,
    )
    write_tsv(
        UNRESOLVED_FILE,
        fields,
        unresolved,
    )

    summary_rows: list[dict[str, object]] = []

    for stage in STAGES:
        summary_rows.append(
            {
                "stage": stage,
                "input_candidates": (
                    stage_input_count[stage]
                ),
                "manual_review_candidates": (
                    stage_review_count[stage]
                ),
                "excluded_candidates": (
                    stage_excluded_count[stage]
                ),
                "unresolved_candidates": (
                    stage_unresolved_count[stage]
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    write_tsv(
        SUMMARY_FILE,
        (
            "stage",
            "input_candidates",
            "manual_review_candidates",
            "excluded_candidates",
            "unresolved_candidates",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        summary_rows,
    )

    stages_without_review = [
        stage
        for stage in STAGES
        if stage_review_count[stage] == 0
    ]

    print(
        "=== AUDIT DECISION OWNER "
        "CANDIDATE REDUCTION V1 ==="
    )
    print(f"input_candidate_count={len(candidates)}")
    print(f"manual_review_count={len(reduced)}")
    print(f"excluded_count={len(excluded)}")
    print(f"unresolved_count={len(unresolved)}")
    print(
        f"stage_without_review_candidate_count="
        f"{len(stages_without_review)}"
    )

    for stage in STAGES:
        print(
            f"STAGE name={stage} "
            f"input={stage_input_count[stage]} "
            f"review={stage_review_count[stage]} "
            f"excluded={stage_excluded_count[stage]} "
            f"unresolved={stage_unresolved_count[stage]}"
        )

        for row in (
            candidate
            for candidate in reduced
            if candidate["stage"] == stage
        ):
            print(
                f"REVIEW_CANDIDATE stage={stage} "
                f"score={row['score']} "
                f"path={row['path']} "
                f"function={row['function']} "
                f"line={row['line']}"
            )

    for stage in stages_without_review:
        print(
            f"UNRESOLVED_STAGE stage={stage} "
            "reason=no_product_runtime_candidate"
        )

    print(f"reduced_file={REDUCED_FILE}")
    print(f"excluded_file={EXCLUDED_FILE}")
    print(f"summary_file={SUMMARY_FILE}")
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
        "DECISION_OWNER_CANDIDATE_REDUCTION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
