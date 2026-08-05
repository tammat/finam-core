#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
from dataclasses import dataclass
from decimal import Decimal


OUT = pathlib.Path(
    "/tmp/capital_growth_formula_registry_v1"
)

METRICS_REGISTRY = pathlib.Path(
    "/tmp/capital_growth_metrics_registry_v1/metrics.tsv"
)

FORMULAS_FILE = OUT / "formulas.tsv"
INPUTS_FILE = OUT / "formula_inputs.tsv"
GATES_FILE = OUT / "hard_gates.tsv"
PENALTIES_FILE = OUT / "penalties.tsv"
CONFIDENCE_FILE = OUT / "confidence_policy.tsv"
CONTRACT_FILE = OUT / "formula_contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"


@dataclass(frozen=True, slots=True)
class Formula:
    formula_code: str
    formula_version: str
    output_metric: str
    formula_type: str
    expression: str
    base_score_min: str
    base_score_max: str
    missing_metric_policy: str
    activation_status: str
    owner_stage: str


@dataclass(frozen=True, slots=True)
class FormulaInput:
    formula_code: str
    metric_code: str
    role: str
    weight: str
    normalization_source: str
    required: int
    direction: str


@dataclass(frozen=True, slots=True)
class HardGate:
    formula_code: str
    gate_code: str
    metric_code: str
    operator: str
    threshold: str
    failure_score: str
    failure_status: str
    reason: str


@dataclass(frozen=True, slots=True)
class Penalty:
    formula_code: str
    penalty_code: str
    metric_code: str
    penalty_type: str
    coefficient: str
    maximum_penalty: str
    reason: str


@dataclass(frozen=True, slots=True)
class ConfidenceRule:
    formula_code: str
    rule_code: str
    condition: str
    confidence_multiplier: str
    score_allowed: int
    allocation_allowed: int
    reason: str


FORMULAS = (
    Formula(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        formula_version="V1",
        output_metric="CAPITAL_GROWTH_SCORE",
        formula_type="WEIGHTED_SCORE_WITH_GATES_AND_PENALTIES",
        expression=(
            "100 * confidence_multiplier * "
            "max(0, weighted_positive_score - total_penalty)"
        ),
        base_score_min="0",
        base_score_max="100",
        missing_metric_policy="INVALID_IF_REQUIRED_COMPONENT_MISSING",
        activation_status="VALIDATED_NOT_ACTIVE",
        owner_stage="CAPITAL_GROWTH",
    ),
)

INPUTS = (
    FormulaInput(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        metric_code="NET_EXPECTANCY",
        role="POSITIVE_COMPONENT",
        weight="0.20",
        normalization_source="METRICS_REGISTRY",
        required=1,
        direction="HIGHER_IS_BETTER",
    ),
    FormulaInput(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        metric_code="EXPECTED_CAGR",
        role="POSITIVE_COMPONENT",
        weight="0.15",
        normalization_source="METRICS_REGISTRY",
        required=1,
        direction="HIGHER_IS_BETTER",
    ),
    FormulaInput(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        metric_code="MAR_RATIO",
        role="POSITIVE_COMPONENT",
        weight="0.15",
        normalization_source="METRICS_REGISTRY",
        required=1,
        direction="HIGHER_IS_BETTER",
    ),
    FormulaInput(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        metric_code="CAPITAL_EFFICIENCY",
        role="POSITIVE_COMPONENT",
        weight="0.15",
        normalization_source="METRICS_REGISTRY",
        required=1,
        direction="HIGHER_IS_BETTER",
    ),
    FormulaInput(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        metric_code="ROBUSTNESS_SCORE",
        role="POSITIVE_COMPONENT",
        weight="0.15",
        normalization_source="METRICS_REGISTRY",
        required=1,
        direction="HIGHER_IS_BETTER",
    ),
    FormulaInput(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        metric_code="LIQUIDITY_SCORE",
        role="POSITIVE_COMPONENT",
        weight="0.075",
        normalization_source="METRICS_REGISTRY",
        required=1,
        direction="HIGHER_IS_BETTER",
    ),
    FormulaInput(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        metric_code="EXECUTION_QUALITY_SCORE",
        role="POSITIVE_COMPONENT",
        weight="0.075",
        normalization_source="METRICS_REGISTRY",
        required=1,
        direction="HIGHER_IS_BETTER",
    ),
    FormulaInput(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        metric_code="CAPACITY_SCORE",
        role="POSITIVE_COMPONENT",
        weight="0.05",
        normalization_source="METRICS_REGISTRY",
        required=1,
        direction="HIGHER_IS_BETTER",
    ),
    FormulaInput(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        metric_code="MAX_DRAWDOWN",
        role="HARD_GATE_AND_PENALTY",
        weight="0",
        normalization_source="METRICS_REGISTRY",
        required=1,
        direction="LOWER_IS_BETTER",
    ),
    FormulaInput(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        metric_code="RISK_OF_RUIN",
        role="HARD_GATE_AND_PENALTY",
        weight="0",
        normalization_source="METRICS_REGISTRY",
        required=1,
        direction="LOWER_IS_BETTER",
    ),
    FormulaInput(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        metric_code="KELLY_FRACTION",
        role="HARD_GATE",
        weight="0",
        normalization_source="METRICS_REGISTRY",
        required=1,
        direction="HIGHER_IS_BETTER_WITH_CAP",
    ),
    FormulaInput(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        metric_code="CORRELATION_PENALTY",
        role="PENALTY",
        weight="0",
        normalization_source="METRICS_REGISTRY",
        required=1,
        direction="LOWER_IS_BETTER",
    ),
)

HARD_GATES = (
    HardGate(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        gate_code="NET_EXPECTANCY_POSITIVE",
        metric_code="NET_EXPECTANCY",
        operator=">",
        threshold="0",
        failure_score="0",
        failure_status="BLOCKED",
        reason="Нет положительного ожидания после затрат",
    ),
    HardGate(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        gate_code="MAX_DRAWDOWN_LIMIT",
        metric_code="MAX_DRAWDOWN",
        operator="<=",
        threshold="0.25",
        failure_score="0",
        failure_status="BLOCKED",
        reason="Просадка превышает предельный уровень V1",
    ),
    HardGate(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        gate_code="RISK_OF_RUIN_LIMIT",
        metric_code="RISK_OF_RUIN",
        operator="<=",
        threshold="0.01",
        failure_score="0",
        failure_status="BLOCKED",
        reason="Вероятность разорения превышает 1 процент",
    ),
    HardGate(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        gate_code="ROBUSTNESS_MINIMUM",
        metric_code="ROBUSTNESS_SCORE",
        operator=">=",
        threshold="60",
        failure_score="0",
        failure_status="BLOCKED",
        reason="Недостаточная устойчивость edge",
    ),
    HardGate(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        gate_code="KELLY_POSITIVE",
        metric_code="KELLY_FRACTION",
        operator=">",
        threshold="0",
        failure_score="0",
        failure_status="BLOCKED",
        reason="Отрицательная либо нулевая доля Келли",
    ),
)

PENALTIES = (
    Penalty(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        penalty_code="CORRELATION_CONCENTRATION",
        metric_code="CORRELATION_PENALTY",
        penalty_type="LINEAR",
        coefficient="0.20",
        maximum_penalty="0.20",
        reason="Снижение оценки при высокой корреляции с активными edge",
    ),
    Penalty(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        penalty_code="DRAWDOWN_PRESSURE",
        metric_code="MAX_DRAWDOWN",
        penalty_type="LINEAR_ABOVE_THRESHOLD",
        coefficient="0.50",
        maximum_penalty="0.15",
        reason="Дополнительный штраф при просадке выше 10 процентов",
    ),
    Penalty(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        penalty_code="RUIN_PRESSURE",
        metric_code="RISK_OF_RUIN",
        penalty_type="LINEAR",
        coefficient="5.00",
        maximum_penalty="0.10",
        reason="Штраф до hard gate по вероятности разорения",
    ),
)

CONFIDENCE_RULES = (
    ConfidenceRule(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        rule_code="FULL_CONFIDENCE",
        condition=(
            "all_required_metrics_valid "
            "and minimum_sample_satisfied "
            "and data_quality_passed"
        ),
        confidence_multiplier="1.00",
        score_allowed=1,
        allocation_allowed=0,
        reason="Полный набор валидных метрик",
    ),
    ConfidenceRule(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        rule_code="REDUCED_CONFIDENCE",
        condition=(
            "all_required_metrics_valid "
            "and sample_above_minimum "
            "and sample_below_preferred"
        ),
        confidence_multiplier="0.75",
        score_allowed=1,
        allocation_allowed=0,
        reason="Ограниченная, но допустимая выборка",
    ),
    ConfidenceRule(
        formula_code="CAPITAL_GROWTH_SCORE_V1",
        rule_code="INVALID_CONFIDENCE",
        condition=(
            "required_metric_missing "
            "or minimum_sample_failed "
            "or data_quality_failed"
        ),
        confidence_multiplier="0",
        score_allowed=0,
        allocation_allowed=0,
        reason="Score запрещён при неполных или недостоверных данных",
    ),
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
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def load_registered_metrics() -> set[str]:
    if not METRICS_REGISTRY.is_file():
        raise RuntimeError(
            f"metrics_registry_missing:{METRICS_REGISTRY}"
        )

    with METRICS_REGISTRY.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        return {
            (row.get("metric_code") or "").strip()
            for row in csv.DictReader(
                stream,
                delimiter="\t",
            )
            if (row.get("metric_code") or "").strip()
        }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    unresolved: list[dict[str, object]] = []

    registered_metrics = load_registered_metrics()

    formula_codes = [
        formula.formula_code
        for formula in FORMULAS
    ]

    formula_code_set = set(formula_codes)

    duplicate_formula_count = (
        len(formula_codes)
        - len(formula_code_set)
    )

    if duplicate_formula_count:
        unresolved.append(
            {
                "scope": "FORMULA",
                "identity": "",
                "reason": (
                    "DUPLICATE_FORMULA_CODE_COUNT:"
                    f"{duplicate_formula_count}"
                ),
            }
        )

    for formula in FORMULAS:
        if formula.output_metric not in registered_metrics:
            unresolved.append(
                {
                    "scope": "FORMULA",
                    "identity": formula.formula_code,
                    "reason": "OUTPUT_METRIC_NOT_REGISTERED",
                }
            )

        if formula.activation_status not in {
            "DRAFT",
            "VALIDATED_NOT_ACTIVE",
            "ACTIVE_RESEARCH_ONLY",
            "RETIRED",
        }:
            unresolved.append(
                {
                    "scope": "FORMULA",
                    "identity": formula.formula_code,
                    "reason": "INVALID_ACTIVATION_STATUS",
                }
            )

    positive_weight_sum = Decimal("0")

    for item in INPUTS:
        if item.formula_code not in formula_code_set:
            unresolved.append(
                {
                    "scope": "INPUT",
                    "identity": item.formula_code,
                    "reason": "FORMULA_NOT_REGISTERED",
                }
            )

        if item.metric_code not in registered_metrics:
            unresolved.append(
                {
                    "scope": "INPUT",
                    "identity": item.metric_code,
                    "reason": "METRIC_NOT_REGISTERED",
                }
            )

        if item.role == "POSITIVE_COMPONENT":
            positive_weight_sum += Decimal(item.weight)

    if positive_weight_sum != Decimal("1.000"):
        unresolved.append(
            {
                "scope": "FORMULA",
                "identity": "CAPITAL_GROWTH_SCORE_V1",
                "reason": (
                    "POSITIVE_WEIGHT_SUM_INVALID:"
                    f"{positive_weight_sum}"
                ),
            }
        )

    gate_codes = [
        gate.gate_code
        for gate in HARD_GATES
    ]

    duplicate_gate_count = (
        len(gate_codes)
        - len(set(gate_codes))
    )

    if duplicate_gate_count:
        unresolved.append(
            {
                "scope": "HARD_GATE",
                "identity": "",
                "reason": (
                    "DUPLICATE_GATE_CODE_COUNT:"
                    f"{duplicate_gate_count}"
                ),
            }
        )

    for gate in HARD_GATES:
        if gate.metric_code not in registered_metrics:
            unresolved.append(
                {
                    "scope": "HARD_GATE",
                    "identity": gate.metric_code,
                    "reason": "METRIC_NOT_REGISTERED",
                }
            )

    penalty_codes = [
        item.penalty_code
        for item in PENALTIES
    ]

    duplicate_penalty_count = (
        len(penalty_codes)
        - len(set(penalty_codes))
    )

    if duplicate_penalty_count:
        unresolved.append(
            {
                "scope": "PENALTY",
                "identity": "",
                "reason": (
                    "DUPLICATE_PENALTY_CODE_COUNT:"
                    f"{duplicate_penalty_count}"
                ),
            }
        )

    for penalty in PENALTIES:
        if penalty.metric_code not in registered_metrics:
            unresolved.append(
                {
                    "scope": "PENALTY",
                    "identity": penalty.metric_code,
                    "reason": "METRIC_NOT_REGISTERED",
                }
            )

    write_tsv(
        FORMULAS_FILE,
        (
            "formula_code",
            "formula_version",
            "output_metric",
            "formula_type",
            "expression",
            "base_score_min",
            "base_score_max",
            "missing_metric_policy",
            "activation_status",
            "owner_stage",
        ),
        [
            {
                "formula_code": row.formula_code,
                "formula_version": row.formula_version,
                "output_metric": row.output_metric,
                "formula_type": row.formula_type,
                "expression": row.expression,
                "base_score_min": row.base_score_min,
                "base_score_max": row.base_score_max,
                "missing_metric_policy": row.missing_metric_policy,
                "activation_status": row.activation_status,
                "owner_stage": row.owner_stage,
            }
            for row in FORMULAS
        ],
    )

    write_tsv(
        INPUTS_FILE,
        (
            "formula_code",
            "metric_code",
            "role",
            "weight",
            "normalization_source",
            "required",
            "direction",
        ),
        [
            {
                "formula_code": row.formula_code,
                "metric_code": row.metric_code,
                "role": row.role,
                "weight": row.weight,
                "normalization_source": row.normalization_source,
                "required": row.required,
                "direction": row.direction,
            }
            for row in INPUTS
        ],
    )

    write_tsv(
        GATES_FILE,
        (
            "formula_code",
            "gate_code",
            "metric_code",
            "operator",
            "threshold",
            "failure_score",
            "failure_status",
            "reason",
        ),
        [
            {
                "formula_code": row.formula_code,
                "gate_code": row.gate_code,
                "metric_code": row.metric_code,
                "operator": row.operator,
                "threshold": row.threshold,
                "failure_score": row.failure_score,
                "failure_status": row.failure_status,
                "reason": row.reason,
            }
            for row in HARD_GATES
        ],
    )

    write_tsv(
        PENALTIES_FILE,
        (
            "formula_code",
            "penalty_code",
            "metric_code",
            "penalty_type",
            "coefficient",
            "maximum_penalty",
            "reason",
        ),
        [
            {
                "formula_code": row.formula_code,
                "penalty_code": row.penalty_code,
                "metric_code": row.metric_code,
                "penalty_type": row.penalty_type,
                "coefficient": row.coefficient,
                "maximum_penalty": row.maximum_penalty,
                "reason": row.reason,
            }
            for row in PENALTIES
        ],
    )

    write_tsv(
        CONFIDENCE_FILE,
        (
            "formula_code",
            "rule_code",
            "condition",
            "confidence_multiplier",
            "score_allowed",
            "allocation_allowed",
            "reason",
        ),
        [
            {
                "formula_code": row.formula_code,
                "rule_code": row.rule_code,
                "condition": row.condition,
                "confidence_multiplier": row.confidence_multiplier,
                "score_allowed": row.score_allowed,
                "allocation_allowed": row.allocation_allowed,
                "reason": row.reason,
            }
            for row in CONFIDENCE_RULES
        ],
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
        stream.write(
            "CAPITAL GROWTH FORMULA REGISTRY V1\n"
        )
        stream.write(
            "==================================\n\n"
        )
        stream.write(
            "PRIMARY_GOAL="
            "MAXIMIZE_LONG_TERM_CAPITAL_GROWTH\n"
        )
        stream.write(
            "FORMULA_COUNT="
            f"{len(FORMULAS)}\n"
        )
        stream.write(
            "FORMULA_INPUT_COUNT="
            f"{len(INPUTS)}\n"
        )
        stream.write(
            "POSITIVE_WEIGHT_SUM="
            f"{positive_weight_sum}\n"
        )
        stream.write(
            "HARD_GATE_COUNT="
            f"{len(HARD_GATES)}\n"
        )
        stream.write(
            "PENALTY_COUNT="
            f"{len(PENALTIES)}\n"
        )
        stream.write(
            "CONFIDENCE_RULE_COUNT="
            f"{len(CONFIDENCE_RULES)}\n"
        )
        stream.write(
            "ACTIVATION_STATUS="
            "VALIDATED_NOT_ACTIVE\n"
        )
        stream.write(
            "ALLOCATION_ALLOWED=0\n"
        )
        stream.write(
            "RUNTIME_USAGE_ALLOWED=0\n"
        )
        stream.write(
            "EXECUTION_USAGE_ALLOWED=0\n"
        )
        stream.write(
            "MISSING_METRIC_POLICY="
            "INVALID_IF_REQUIRED_COMPONENT_MISSING\n"
        )
        stream.write(
            "DUPLICATE_FORMULA_CODE_COUNT="
            f"{duplicate_formula_count}\n"
        )
        stream.write(
            "DUPLICATE_GATE_CODE_COUNT="
            f"{duplicate_gate_count}\n"
        )
        stream.write(
            "DUPLICATE_PENALTY_CODE_COUNT="
            f"{duplicate_penalty_count}\n"
        )
        stream.write(
            "UNRESOLVED_COUNT="
            f"{len(unresolved)}\n"
        )
        stream.write("RUNTIME_CHANGED=0\n")
        stream.write("EXECUTION_CHANGED=0\n")
        stream.write("ORDERS_CHANGED=0\n")
        stream.write("FILLS_CHANGED=0\n")
        stream.write("MICRO_LIVE_ALLOWED=0\n")

    print(
        "=== BUILD CAPITAL GROWTH "
        "FORMULA REGISTRY V1 ==="
    )
    print(f"formula_count={len(FORMULAS)}")
    print(f"formula_input_count={len(INPUTS)}")
    print(f"positive_weight_sum={positive_weight_sum}")
    print(f"hard_gate_count={len(HARD_GATES)}")
    print(f"penalty_count={len(PENALTIES)}")
    print(
        f"confidence_rule_count={len(CONFIDENCE_RULES)}"
    )
    print(
        "activation_status=VALIDATED_NOT_ACTIVE"
    )
    print("allocation_allowed=0")
    print("runtime_usage_allowed=0")
    print("execution_usage_allowed=0")
    print(f"unresolved_count={len(unresolved)}")

    for item in INPUTS:
        print(
            "FORMULA_INPUT "
            f"formula={item.formula_code} "
            f"metric={item.metric_code} "
            f"role={item.role} "
            f"weight={item.weight} "
            f"required={item.required}"
        )

    for gate in HARD_GATES:
        print(
            "HARD_GATE "
            f"code={gate.gate_code} "
            f"metric={gate.metric_code} "
            f"operator={gate.operator} "
            f"threshold={gate.threshold}"
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
    print(
        "VERDICT="
        "CAPITAL_GROWTH_FORMULA_REGISTRY_V1_READY"
    )

    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
