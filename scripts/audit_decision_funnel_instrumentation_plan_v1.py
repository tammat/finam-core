#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable


ROOT = pathlib.Path("/opt/finam-core").resolve()
SRC = ROOT / "src"
OUTPUT_DIR = pathlib.Path(
    "/tmp/decision_funnel_instrumentation_plan_v1"
)

PLAN_FILE = OUTPUT_DIR / "instrumentation_plan.txt"
POINTS_FILE = OUTPUT_DIR / "instrumentation_points.tsv"
SIGNAL_ID_FILE = OUTPUT_DIR / "signal_id_candidates.tsv"
BOUNDARIES_FILE = OUTPUT_DIR / "transaction_boundaries.tsv"
POLICY_FILE = OUTPUT_DIR / "recorder_policy.tsv"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved.tsv"

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "tests",
}

STAGES: tuple[str, ...] = (
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

STAGE_MARKERS: dict[str, tuple[str, ...]] = {
    "MARKET_DATA": (
        "market_data",
        "market_bar",
        "bars",
        "candle",
        "quote",
        "snapshot",
        "freshness",
        "stale",
    ),
    "STRATEGY": (
        "strategy",
        "signal",
        "generate_signal",
        "build_signal",
        "evaluate_signal",
        "no_signal",
    ),
    "REGIME": (
        "regime",
        "market_regime",
        "regime_filter",
        "allowed_regime",
    ),
    "EDGE": (
        "edge_score",
        "edge",
        "confidence",
        "expectancy",
        "profit_factor",
        "sample_size",
    ),
    "RISK": (
        "risk_engine",
        "risk",
        "max_risk_per_trade",
        "daily_loss_limit",
        "kill_switch",
        "correlation_filter",
    ),
    "PORTFOLIO": (
        "portfolio",
        "position",
        "exposure",
        "capital",
        "already_open",
    ),
    "RUNTIME": (
        "runtime_allow",
        "runtime_allowed",
        "runtime_governance",
        "micro_live_allowed",
        "paper_only",
        "shadow_only",
    ),
    "EXECUTION": (
        "execution",
        "execution_enabled",
        "submit_order",
        "place_order",
        "send_order",
        "order_request",
    ),
    "BROKER": (
        "broker",
        "finam_client",
        "order_ack",
        "broker_reject",
        "order_status",
    ),
    "FILL": (
        "fill",
        "fills",
        "filled",
        "partial_fill",
        "execution_report",
        "reconcile",
    ),
}

DECISION_MARKERS = (
    "allowed",
    "should_send",
    "should_execute",
    "approved",
    "rejected",
    "reject",
    "blocked",
    "skip",
    "decision",
    "reason",
    "verdict",
)

SIGNAL_ID_MARKERS = (
    "signal_id",
    "trade_signal_id",
    "decision_id",
    "intent_id",
    "correlation_id",
    "event_id",
    "client_order_id",
    "order_id",
)

TRANSACTION_MARKERS = (
    "commit",
    "rollback",
    "transaction",
    "autocommit",
    "cursor",
    "execute",
    "executemany",
    "send_order",
    "submit_order",
    "place_order",
    "requests.post",
    "grpc",
)

MUTATION_CALLS = {
    "commit",
    "rollback",
    "execute",
    "executemany",
    "send_order",
    "submit_order",
    "place_order",
    "post",
    "put",
    "delete",
}

RECORDER_POLICY: dict[str, str] = {
    stage: "FAIL_OPEN"
    for stage in STAGES
}


@dataclass(frozen=True, slots=True)
class FunctionInfo:
    path: pathlib.Path
    qualified_name: str
    line: int
    end_line: int
    source: str
    calls: tuple[str, ...]
    names: tuple[str, ...]
    returns: tuple[str, ...]
    mutation_calls: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Candidate:
    stage: str
    score: int
    path: str
    function: str
    line: int
    decision_markers: str
    stage_markers: str
    mutation_calls: str
    classification: str


class FunctionVisitor(ast.NodeVisitor):
    def __init__(
        self,
        *,
        path: pathlib.Path,
        source: str,
    ) -> None:
        self.path = path
        self.source = source
        self.stack: list[str] = []
        self.functions: list[FunctionInfo] = []

    @staticmethod
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

    @staticmethod
    def return_shape(node: ast.Return) -> str:
        value = node.value

        if value is None:
            return "None"

        if isinstance(value, ast.Name):
            return f"Name:{value.id}"

        if isinstance(value, ast.Constant):
            return f"Constant:{value.value!r}"

        if isinstance(value, ast.Call):
            return f"Call:{FunctionVisitor.call_name(value)}"

        if isinstance(value, ast.Dict):
            return "Dict"

        if isinstance(value, ast.Tuple):
            return "Tuple"

        return type(value).__name__

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        qualified = ".".join(
            [*self.stack, node.name]
        )

        segment = ast.get_source_segment(
            self.source,
            node,
        ) or ""

        calls: list[str] = []
        names: set[str] = set()
        returns: list[str] = []
        mutations: list[str] = []

        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                names.add(child.id)

            elif isinstance(child, ast.Attribute):
                names.add(child.attr)

            elif isinstance(child, ast.Call):
                call = self.call_name(child)
                calls.append(call)

                terminal = call.rsplit(".", 1)[-1]

                if terminal in MUTATION_CALLS:
                    mutations.append(call)

            elif isinstance(child, ast.Return):
                returns.append(
                    self.return_shape(child)
                )

        self.functions.append(
            FunctionInfo(
                path=self.path,
                qualified_name=qualified,
                line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                source=segment,
                calls=tuple(sorted(set(calls))),
                names=tuple(sorted(names)),
                returns=tuple(returns),
                mutation_calls=tuple(
                    sorted(set(mutations))
                ),
            )
        )

        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(
        self,
        node: ast.FunctionDef,
    ) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> None:
        self._visit_function(node)


def python_files() -> list[pathlib.Path]:
    result: list[pathlib.Path] = []

    for path in SRC.rglob("*.py"):
        relative_parts = set(
            path.relative_to(ROOT).parts
        )

        if relative_parts & EXCLUDED_PARTS:
            continue

        result.append(path)

    return sorted(result)


def inspect_functions() -> tuple[
    list[FunctionInfo],
    list[tuple[str, str]],
]:
    functions: list[FunctionInfo] = []
    parse_errors: list[tuple[str, str]] = []

    for path in python_files():
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            parse_errors.append(
                (
                    str(path.relative_to(ROOT)),
                    f"{exc.msg}:{exc.lineno}",
                )
            )
            continue

        visitor = FunctionVisitor(
            path=path,
            source=source,
        )
        visitor.visit(tree)
        functions.extend(visitor.functions)

    return functions, parse_errors


def normalized_text(function: FunctionInfo) -> str:
    values = [
        function.qualified_name,
        function.source,
        *function.calls,
        *function.names,
        *function.returns,
    ]

    return "\n".join(values).lower()


def matching_markers(
    text: str,
    markers: Iterable[str],
) -> tuple[str, ...]:
    return tuple(
        marker
        for marker in markers
        if marker.lower() in text
    )


def classify_candidate(
    function: FunctionInfo,
    stage: str,
) -> Candidate | None:
    text = normalized_text(function)

    stage_hits = matching_markers(
        text,
        STAGE_MARKERS[stage],
    )

    if not stage_hits:
        return None

    decision_hits = matching_markers(
        text,
        DECISION_MARKERS,
    )

    score = (
        len(stage_hits) * 3
        + len(decision_hits) * 2
    )

    if function.returns:
        score += 1

    if function.mutation_calls:
        score += 1

    if score < 4:
        return None

    if decision_hits and function.returns:
        classification = "DECISION_POINT_CANDIDATE"
    elif function.mutation_calls:
        classification = "SIDE_EFFECT_BOUNDARY_CANDIDATE"
    else:
        classification = "CONTEXT_PROVIDER_CANDIDATE"

    return Candidate(
        stage=stage,
        score=score,
        path=str(
            function.path.relative_to(ROOT)
        ),
        function=function.qualified_name,
        line=function.line,
        decision_markers=",".join(decision_hits),
        stage_markers=",".join(stage_hits),
        mutation_calls=",".join(
            function.mutation_calls
        ),
        classification=classification,
    )


def build_candidates(
    functions: list[FunctionInfo],
) -> dict[str, list[Candidate]]:
    by_stage: dict[str, list[Candidate]] = {
        stage: []
        for stage in STAGES
    }

    for function in functions:
        for stage in STAGES:
            candidate = classify_candidate(
                function,
                stage,
            )

            if candidate is not None:
                by_stage[stage].append(candidate)

    for stage in STAGES:
        by_stage[stage].sort(
            key=lambda item: (
                -item.score,
                item.path,
                item.line,
            )
        )

    return by_stage


def signal_id_candidates(
    functions: list[FunctionInfo],
) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []

    for function in functions:
        text = normalized_text(function)
        hits = matching_markers(
            text,
            SIGNAL_ID_MARKERS,
        )

        if not hits:
            continue

        creation_markers = matching_markers(
            text,
            (
                "uuid4",
                "uuid.uuid4",
                "new_id",
                "generate_id",
                "hashlib",
                "client_order_id",
            ),
        )

        rows.append(
            {
                "path": str(
                    function.path.relative_to(ROOT)
                ),
                "function": function.qualified_name,
                "line": function.line,
                "id_markers": ",".join(hits),
                "creation_markers": ",".join(
                    creation_markers
                ),
                "returns": ",".join(
                    function.returns
                ),
                "score": (
                    len(hits) * 3
                    + len(creation_markers) * 5
                ),
            }
        )

    rows.sort(
        key=lambda row: (
            -int(row["score"]),
            str(row["path"]),
            int(row["line"]),
        )
    )

    return rows


def transaction_boundaries(
    functions: list[FunctionInfo],
) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []

    for function in functions:
        text = normalized_text(function)
        hits = matching_markers(
            text,
            TRANSACTION_MARKERS,
        )

        if not hits:
            continue

        rows.append(
            {
                "path": str(
                    function.path.relative_to(ROOT)
                ),
                "function": function.qualified_name,
                "line": function.line,
                "markers": ",".join(hits),
                "mutation_calls": ",".join(
                    function.mutation_calls
                ),
                "boundary_type": (
                    "SIDE_EFFECT_BOUNDARY"
                    if function.mutation_calls
                    else "READ_ORCHESTRATION_BOUNDARY"
                ),
            }
        )

    rows.sort(
        key=lambda row: (
            str(row["path"]),
            int(row["line"]),
        )
    )

    return rows


def tracked_reference_count(
    relative_path: str,
) -> int:
    result = subprocess.run(
        [
            "git",
            "grep",
            "-n",
            "--fixed-strings",
            relative_path,
            "--",
            "src",
            "scripts",
            "deploy",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )

    return len(
        [
            line
            for line in result.stdout.splitlines()
            if line.strip()
        ]
    )


def write_tsv(
    path: pathlib.Path,
    fieldnames: list[str],
    rows: Iterable[dict[str, object]],
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

    functions, parse_errors = inspect_functions()
    candidates = build_candidates(functions)
    id_rows = signal_id_candidates(functions)
    boundary_rows = transaction_boundaries(functions)

    point_rows: list[dict[str, object]] = []
    unresolved_rows: list[dict[str, object]] = []

    for stage in STAGES:
        stage_candidates = candidates[stage]
        top = stage_candidates[:10]

        if not top:
            unresolved_rows.append(
                {
                    "scope": "STAGE",
                    "name": stage,
                    "reason": (
                        "NO_CONFIRMED_DECISION_POINT_CANDIDATE"
                    ),
                }
            )

        for rank, candidate in enumerate(
            top,
            start=1,
        ):
            point_rows.append(
                {
                    "stage": candidate.stage,
                    "rank": rank,
                    "score": candidate.score,
                    "path": candidate.path,
                    "function": candidate.function,
                    "line": candidate.line,
                    "classification": (
                        candidate.classification
                    ),
                    "stage_markers": (
                        candidate.stage_markers
                    ),
                    "decision_markers": (
                        candidate.decision_markers
                    ),
                    "mutation_calls": (
                        candidate.mutation_calls
                    ),
                    "tracked_references": (
                        tracked_reference_count(
                            candidate.path
                        )
                    ),
                    "recorder_policy": (
                        RECORDER_POLICY[stage]
                    ),
                    "instrumentation_enabled": 0,
                }
            )

    for path, error in parse_errors:
        unresolved_rows.append(
            {
                "scope": "PYTHON_PARSE",
                "name": path,
                "reason": error,
            }
        )

    if not id_rows:
        unresolved_rows.append(
            {
                "scope": "SIGNAL_ID",
                "name": "signal_id",
                "reason": (
                    "NO_STABLE_SIGNAL_ID_SOURCE_CONFIRMED"
                ),
            }
        )

    policy_rows = [
        {
            "stage": stage,
            "recorder_failure_policy": (
                RECORDER_POLICY[stage]
            ),
            "trading_decision_owner": (
                "EXISTING_COMPONENT"
            ),
            "recorder_decision_authority": 0,
            "recorder_order_authority": 0,
            "recorder_runtime_authority": 0,
            "instrumentation_enabled": 0,
        }
        for stage in STAGES
    ]

    write_tsv(
        POINTS_FILE,
        [
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
            "recorder_policy",
            "instrumentation_enabled",
        ],
        point_rows,
    )

    write_tsv(
        SIGNAL_ID_FILE,
        [
            "path",
            "function",
            "line",
            "id_markers",
            "creation_markers",
            "returns",
            "score",
        ],
        id_rows,
    )

    write_tsv(
        BOUNDARIES_FILE,
        [
            "path",
            "function",
            "line",
            "markers",
            "mutation_calls",
            "boundary_type",
        ],
        boundary_rows,
    )

    write_tsv(
        POLICY_FILE,
        [
            "stage",
            "recorder_failure_policy",
            "trading_decision_owner",
            "recorder_decision_authority",
            "recorder_order_authority",
            "recorder_runtime_authority",
            "instrumentation_enabled",
        ],
        policy_rows,
    )

    write_tsv(
        UNRESOLVED_FILE,
        [
            "scope",
            "name",
            "reason",
        ],
        unresolved_rows,
    )

    with PLAN_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "DECISION FUNNEL INSTRUMENTATION PLAN V1\n"
        )
        stream.write(
            "=======================================\n\n"
        )
        stream.write(
            "STATUS=PLAN_ONLY\n"
        )
        stream.write(
            "RUNTIME_INSTRUMENTATION=0\n"
        )
        stream.write(
            "RECORDER_FAILURE_POLICY=FAIL_OPEN\n"
        )
        stream.write(
            "RECORDER_TRADING_AUTHORITY=0\n"
        )
        stream.write(
            "RECORDER_ORDER_AUTHORITY=0\n\n"
        )

        for stage in STAGES:
            rows = candidates[stage][:3]
            stream.write(f"[{stage}]\n")

            if not rows:
                stream.write(
                    "STATUS=UNRESOLVED\n\n"
                )
                continue

            for rank, candidate in enumerate(
                rows,
                start=1,
            ):
                stream.write(
                    f"CANDIDATE rank={rank} "
                    f"score={candidate.score} "
                    f"path={candidate.path} "
                    f"function={candidate.function} "
                    f"line={candidate.line} "
                    f"classification="
                    f"{candidate.classification}\n"
                )

            stream.write("\n")

        stream.write("[SIGNAL_ID]\n")

        if id_rows:
            for rank, row in enumerate(
                id_rows[:10],
                start=1,
            ):
                stream.write(
                    f"CANDIDATE rank={rank} "
                    f"score={row['score']} "
                    f"path={row['path']} "
                    f"function={row['function']} "
                    f"line={row['line']} "
                    f"markers={row['id_markers']} "
                    f"creation={row['creation_markers']}\n"
                )
        else:
            stream.write(
                "STATUS=UNRESOLVED\n"
            )

        stream.write("\n")
        stream.write("[RECORDER_CONTRACT]\n")
        stream.write(
            "INPUT=signal_id,symbol,strategy,timeframe,"
            "stage,outcome,reason,context,occurred_at\n"
        )
        stream.write(
            "OUTPUT=SignalDecisionEvent\n"
        )
        stream.write(
            "FAILURE_POLICY=FAIL_OPEN\n"
        )
        stream.write(
            "MUST_NOT_CHANGE_EXISTING_DECISION=1\n"
        )
        stream.write(
            "MUST_NOT_SEND_ORDER=1\n"
        )
        stream.write(
            "MUST_NOT_CHANGE_RUNTIME=1\n"
        )
        stream.write(
            "MUST_NOT_SHARE_TRADING_TRANSACTION=1\n"
        )

    resolved_stages = sum(
        1
        for stage in STAGES
        if candidates[stage]
    )

    print(
        "=== AUDIT DECISION FUNNEL "
        "INSTRUMENTATION PLAN V1 ==="
    )
    print(f"python_files_scanned={len(python_files())}")
    print(f"functions_scanned={len(functions)}")
    print(f"parse_errors={len(parse_errors)}")
    print(f"stage_count={len(STAGES)}")
    print(f"resolved_stage_count={resolved_stages}")
    print(
        f"unresolved_stage_count="
        f"{len(STAGES) - resolved_stages}"
    )

    for stage in STAGES:
        rows = candidates[stage]
        print(
            f"STAGE name={stage} "
            f"candidate_count={len(rows)}"
        )

        for candidate in rows[:3]:
            print(
                f"CANDIDATE stage={stage} "
                f"score={candidate.score} "
                f"path={candidate.path} "
                f"function={candidate.function} "
                f"line={candidate.line} "
                f"classification="
                f"{candidate.classification}"
            )

    print(
        f"signal_id_candidate_count={len(id_rows)}"
    )
    print(
        f"transaction_boundary_count="
        f"{len(boundary_rows)}"
    )
    print(
        f"unresolved_count={len(unresolved_rows)}"
    )

    print(f"plan_file={PLAN_FILE}")
    print(f"points_file={POINTS_FILE}")
    print(f"signal_id_file={SIGNAL_ID_FILE}")
    print(f"boundaries_file={BOUNDARIES_FILE}")
    print(f"policy_file={POLICY_FILE}")
    print(f"unresolved_file={UNRESOLVED_FILE}")

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
        "DECISION_FUNNEL_INSTRUMENTATION_PLAN_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
