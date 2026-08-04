#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
from dataclasses import dataclass


ROOT = pathlib.Path("/opt/finam-core").resolve()

INPUT = pathlib.Path(
    "/tmp/decision_owner_candidate_reduction_v1/"
    "reduced_candidates.tsv"
)

OUTPUT_DIR = pathlib.Path(
    "/tmp/decision_owner_priority_evidence_v1"
)

CANDIDATES_FILE = OUTPUT_DIR / "priority_candidates.tsv"
EVIDENCE_FILE = OUTPUT_DIR / "function_evidence.txt"
CALLS_FILE = OUTPUT_DIR / "call_relationships.tsv"
RETURNS_FILE = OUTPUT_DIR / "return_contracts.tsv"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved.tsv"

PRIORITY_STAGES = (
    "STRATEGY",
    "RISK",
    "RUNTIME",
    "EXECUTION",
    "BROKER",
)

DECISION_WORDS = (
    "allow",
    "allowed",
    "approve",
    "approved",
    "reject",
    "rejected",
    "deny",
    "denied",
    "block",
    "blocked",
    "skip",
    "decision",
    "reason",
    "verdict",
)

SIDE_EFFECT_WORDS = (
    "send_order",
    "place_order",
    "submit_order",
    "cancel_order",
    "replace_order",
    "commit",
    "execute",
)

READ_ONLY_WORDS = (
    "select",
    "fetch",
    "get",
    "load",
    "read",
    "resolve",
)


@dataclass(frozen=True, slots=True)
class Candidate:
    stage: str
    score: int
    path: str
    function: str
    line: int
    mutation_calls: str


@dataclass(frozen=True, slots=True)
class FunctionEvidence:
    candidate: Candidate
    qualified_name: str
    line: int
    end_line: int
    source: str
    calls: tuple[str, ...]
    returns: tuple[str, ...]
    raises: tuple[str, ...]
    decision_hits: tuple[str, ...]
    side_effect_hits: tuple[str, ...]
    read_only_hits: tuple[str, ...]


def read_candidates() -> list[Candidate]:
    if not INPUT.is_file():
        raise RuntimeError(f"input_missing:{INPUT}")

    rows: list[Candidate] = []

    with INPUT.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        reader = csv.DictReader(
            stream,
            delimiter="\t",
        )

        for raw in reader:
            stage = str(raw["stage"]).strip()

            if stage not in PRIORITY_STAGES:
                continue

            rows.append(
                Candidate(
                    stage=stage,
                    score=int(raw["score"]),
                    path=str(raw["path"]).strip(),
                    function=str(raw["function"]).strip(),
                    line=int(raw["line"]),
                    mutation_calls=str(
                        raw["mutation_calls"]
                    ).strip(),
                )
            )

    rows.sort(
        key=lambda row: (
            PRIORITY_STAGES.index(row.stage),
            -row.score,
            row.path,
            row.line,
        )
    )

    return rows


def call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        parts: list[str] = []
        current: ast.expr = node.func

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return "<unknown>"


def return_shape(node: ast.Return) -> str:
    value = node.value

    if value is None:
        return "None"

    if isinstance(value, ast.Constant):
        return f"Constant:{value.value!r}"

    if isinstance(value, ast.Name):
        return f"Name:{value.id}"

    if isinstance(value, ast.Dict):
        return "Dict"

    if isinstance(value, ast.Tuple):
        return "Tuple"

    if isinstance(value, ast.Call):
        return f"Call:{call_name(value)}"

    return type(value).__name__


def find_function(
    candidate: Candidate,
) -> FunctionEvidence:
    path = ROOT / candidate.path

    if not path.is_file():
        raise RuntimeError(
            f"candidate_file_missing:{candidate.path}"
        )

    source = path.read_text(
        encoding="utf-8",
        errors="replace",
    )
    tree = ast.parse(source)

    matches: list[
        ast.FunctionDef | ast.AsyncFunctionDef
    ] = []

    short_name = candidate.function.rsplit(".", 1)[-1]

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            if (
                node.name == short_name
                and node.lineno == candidate.line
            ):
                matches.append(node)

    if len(matches) != 1:
        raise RuntimeError(
            "candidate_function_not_unique:"
            f"{candidate.path}:"
            f"{candidate.function}:"
            f"{candidate.line}:"
            f"{len(matches)}"
        )

    node = matches[0]
    segment = ast.get_source_segment(
        source,
        node,
    ) or ""

    normalized = segment.lower()

    calls = tuple(
        sorted(
            {
                call_name(child)
                for child in ast.walk(node)
                if isinstance(child, ast.Call)
            }
        )
    )

    returns = tuple(
        return_shape(child)
        for child in ast.walk(node)
        if isinstance(child, ast.Return)
    )

    raises = tuple(
        type(child.exc).__name__
        if child.exc is not None
        else "None"
        for child in ast.walk(node)
        if isinstance(child, ast.Raise)
    )

    decision_hits = tuple(
        word
        for word in DECISION_WORDS
        if word in normalized
    )

    side_effect_hits = tuple(
        word
        for word in SIDE_EFFECT_WORDS
        if word in normalized
    )

    read_only_hits = tuple(
        word
        for word in READ_ONLY_WORDS
        if word in normalized
    )

    return FunctionEvidence(
        candidate=candidate,
        qualified_name=candidate.function,
        line=node.lineno,
        end_line=node.end_lineno or node.lineno,
        source=segment,
        calls=calls,
        returns=returns,
        raises=raises,
        decision_hits=decision_hits,
        side_effect_hits=side_effect_hits,
        read_only_hits=read_only_hits,
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
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidates = read_candidates()
    evidence_rows: list[FunctionEvidence] = []
    unresolved: list[dict[str, object]] = []

    for candidate in candidates:
        try:
            evidence_rows.append(
                find_function(candidate)
            )
        except Exception as exc:
            unresolved.append(
                {
                    "stage": candidate.stage,
                    "path": candidate.path,
                    "function": candidate.function,
                    "line": candidate.line,
                    "reason": str(exc),
                }
            )

    candidate_rows: list[dict[str, object]] = []
    call_rows: list[dict[str, object]] = []
    return_rows: list[dict[str, object]] = []

    with EVIDENCE_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        for evidence in evidence_rows:
            candidate = evidence.candidate

            if evidence.side_effect_hits:
                evidence_class = (
                    "SIDE_EFFECT_BOUNDARY_CANDIDATE"
                )
            elif (
                evidence.decision_hits
                and evidence.returns
            ):
                evidence_class = (
                    "DECISION_OWNER_CANDIDATE"
                )
            elif evidence.calls:
                evidence_class = (
                    "ORCHESTRATOR_OR_GATE_CANDIDATE"
                )
            else:
                evidence_class = "CONTEXT_ONLY_CANDIDATE"

            candidate_rows.append(
                {
                    "stage": candidate.stage,
                    "score": candidate.score,
                    "path": candidate.path,
                    "function": candidate.function,
                    "line": candidate.line,
                    "end_line": evidence.end_line,
                    "evidence_class": evidence_class,
                    "decision_hits": ",".join(
                        evidence.decision_hits
                    ),
                    "side_effect_hits": ",".join(
                        evidence.side_effect_hits
                    ),
                    "call_count": len(evidence.calls),
                    "return_count": len(
                        evidence.returns
                    ),
                    "raise_count": len(
                        evidence.raises
                    ),
                    "owner_confirmed": 0,
                    "runtime_instrumentation": 0,
                }
            )

            for call in evidence.calls:
                call_rows.append(
                    {
                        "stage": candidate.stage,
                        "caller_path": candidate.path,
                        "caller_function": (
                            candidate.function
                        ),
                        "caller_line": candidate.line,
                        "callee": call,
                    }
                )

            for index, shape in enumerate(
                evidence.returns,
                start=1,
            ):
                return_rows.append(
                    {
                        "stage": candidate.stage,
                        "path": candidate.path,
                        "function": candidate.function,
                        "line": candidate.line,
                        "return_index": index,
                        "return_shape": shape,
                    }
                )

            stream.write(
                "=" * 100 + "\n"
            )
            stream.write(
                f"STAGE={candidate.stage}\n"
                f"PATH={candidate.path}\n"
                f"FUNCTION={candidate.function}\n"
                f"LINES={candidate.line}-"
                f"{evidence.end_line}\n"
                f"DECISION_HITS="
                f"{','.join(evidence.decision_hits)}\n"
                f"SIDE_EFFECT_HITS="
                f"{','.join(evidence.side_effect_hits)}\n"
                f"RETURNS="
                f"{','.join(evidence.returns)}\n"
                f"CALLS="
                f"{','.join(evidence.calls)}\n\n"
            )
            stream.write(evidence.source)
            stream.write("\n\n")

    write_tsv(
        CANDIDATES_FILE,
        (
            "stage",
            "score",
            "path",
            "function",
            "line",
            "end_line",
            "evidence_class",
            "decision_hits",
            "side_effect_hits",
            "call_count",
            "return_count",
            "raise_count",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        candidate_rows,
    )

    write_tsv(
        CALLS_FILE,
        (
            "stage",
            "caller_path",
            "caller_function",
            "caller_line",
            "callee",
        ),
        call_rows,
    )

    write_tsv(
        RETURNS_FILE,
        (
            "stage",
            "path",
            "function",
            "line",
            "return_index",
            "return_shape",
        ),
        return_rows,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "stage",
            "path",
            "function",
            "line",
            "reason",
        ),
        unresolved,
    )

    print(
        "=== AUDIT DECISION OWNER "
        "PRIORITY EVIDENCE V1 ==="
    )
    print(
        f"priority_candidate_count="
        f"{len(candidates)}"
    )
    print(
        f"evidence_resolved_count="
        f"{len(evidence_rows)}"
    )
    print(
        f"evidence_unresolved_count="
        f"{len(unresolved)}"
    )

    for row in candidate_rows:
        print(
            f"EVIDENCE stage={row['stage']} "
            f"class={row['evidence_class']} "
            f"path={row['path']} "
            f"function={row['function']} "
            f"line={row['line']} "
            f"calls={row['call_count']} "
            f"returns={row['return_count']}"
        )

    print(f"candidates_file={CANDIDATES_FILE}")
    print(f"evidence_file={EVIDENCE_FILE}")
    print(f"calls_file={CALLS_FILE}")
    print(f"returns_file={RETURNS_FILE}")
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
        "DECISION_OWNER_PRIORITY_EVIDENCE_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
