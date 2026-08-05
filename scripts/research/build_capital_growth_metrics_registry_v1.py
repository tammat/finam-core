#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
from dataclasses import dataclass


OUT = pathlib.Path(
    "/tmp/capital_growth_metrics_registry_v1"
)

METRICS_FILE = OUT / "metrics.tsv"
DEPENDENCIES_FILE = OUT / "metric_dependencies.tsv"
LIFECYCLE_FILE = OUT / "lifecycle_usage.tsv"
CONTRACT_FILE = OUT / "registry_contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"


@dataclass(frozen=True, slots=True)
class Metric:
    code: str
    name_ru: str
    category: str
    metric_level: str
    formula: str
    unit: str
    direction: str
    minimum_sample: int
    calculation_window: str
    valid_min: str
    valid_max: str
    null_policy: str
    source_relation: str
    source_fields: str
    update_frequency: str
    lifecycle_usage: str
    risk_usage: int
    allocation_usage: int
    normalization: str
    owner_stage: str
    version: str


@dataclass(frozen=True, slots=True)
class Dependency:
    metric_code: str
    depends_on_metric_code: str
    dependency_type: str
    required: int


@dataclass(frozen=True, slots=True)
class LifecycleUsage:
    metric_code: str
    lifecycle_status: str
    usage: str
    required: int


METRICS = (
    Metric(
        code="NET_EXPECTANCY",
        name_ru="Чистое математическое ожидание",
        category="ALPHA",
        metric_level="PRIMARY",
        formula=(
            "sum(net_pnl_after_costs) / closed_trade_count"
        ),
        unit="currency_per_trade",
        direction="HIGHER_IS_BETTER",
        minimum_sample=30,
        calculation_window="ROLLING_100_TRADES",
        valid_min="-inf",
        valid_max="+inf",
        null_policy="INVALID_IF_SAMPLE_BELOW_MINIMUM",
        source_relation="analytics.trade_attribution_v3",
        source_fields=(
            "net_pnl_after_costs,trade_status,closed_at"
        ),
        update_frequency="ON_TRADE_CLOSE",
        lifecycle_usage="RESEARCH,ROBUST,OOS_READY,SHADOW_READY,PAPER_READY",
        risk_usage=1,
        allocation_usage=1,
        normalization="ROBUST_Z_SCORE_WINSORIZED",
        owner_stage="CAPITAL_GROWTH",
        version="V1",
    ),
    Metric(
        code="PROFIT_FACTOR",
        name_ru="Профит-фактор",
        category="ALPHA",
        metric_level="PRIMARY",
        formula=(
            "sum(positive_net_pnl) / abs(sum(negative_net_pnl))"
        ),
        unit="ratio",
        direction="HIGHER_IS_BETTER",
        minimum_sample=30,
        calculation_window="ROLLING_100_TRADES",
        valid_min="0",
        valid_max="+inf",
        null_policy="INVALID_IF_NO_GROSS_LOSS",
        source_relation="analytics.trade_attribution_v3",
        source_fields="net_pnl_after_costs,trade_status",
        update_frequency="ON_TRADE_CLOSE",
        lifecycle_usage="RESEARCH,ROBUST,OOS_READY,SHADOW_READY,PAPER_READY",
        risk_usage=0,
        allocation_usage=1,
        normalization="LOG_CLAMPED_0_3",
        owner_stage="CAPITAL_GROWTH",
        version="V1",
    ),
    Metric(
        code="MAX_DRAWDOWN",
        name_ru="Максимальная просадка",
        category="RISK",
        metric_level="PRIMARY",
        formula=(
            "max((running_equity_peak - running_equity) "
            "/ running_equity_peak)"
        ),
        unit="fraction",
        direction="LOWER_IS_BETTER",
        minimum_sample=30,
        calculation_window="FULL_VALIDATION_WINDOW",
        valid_min="0",
        valid_max="1",
        null_policy="INVALID_IF_EQUITY_CURVE_MISSING",
        source_relation="analytics.edge_equity_curve_v1",
        source_fields="equity,observed_at",
        update_frequency="ON_EQUITY_UPDATE",
        lifecycle_usage="ROBUST,OOS_READY,SHADOW_READY,PAPER_READY",
        risk_usage=1,
        allocation_usage=1,
        normalization="INVERSE_CLAMPED_0_1",
        owner_stage="RISK",
        version="V1",
    ),
    Metric(
        code="RECOVERY_FACTOR",
        name_ru="Коэффициент восстановления",
        category="GROWTH",
        metric_level="DERIVED",
        formula="net_profit / max_drawdown_absolute",
        unit="ratio",
        direction="HIGHER_IS_BETTER",
        minimum_sample=30,
        calculation_window="FULL_VALIDATION_WINDOW",
        valid_min="-inf",
        valid_max="+inf",
        null_policy="INVALID_IF_MAX_DRAWDOWN_ZERO_OR_MISSING",
        source_relation="DERIVED",
        source_fields="NET_EXPECTANCY,MAX_DRAWDOWN",
        update_frequency="ON_METRIC_REFRESH",
        lifecycle_usage="ROBUST,OOS_READY,SHADOW_READY,PAPER_READY",
        risk_usage=1,
        allocation_usage=1,
        normalization="LOG_CLAMPED",
        owner_stage="CAPITAL_GROWTH",
        version="V1",
    ),
    Metric(
        code="EXPECTED_CAGR",
        name_ru="Ожидаемый среднегодовой темп роста",
        category="GROWTH",
        metric_level="DERIVED",
        formula=(
            "(ending_equity / starting_equity) "
            "** (365.25 / elapsed_days) - 1"
        ),
        unit="fraction_per_year",
        direction="HIGHER_IS_BETTER",
        minimum_sample=60,
        calculation_window="MINIMUM_90_CALENDAR_DAYS",
        valid_min="-1",
        valid_max="+inf",
        null_policy="INVALID_IF_WINDOW_BELOW_90_DAYS",
        source_relation="analytics.edge_equity_curve_v1",
        source_fields="equity,observed_at",
        update_frequency="DAILY",
        lifecycle_usage="OOS_READY,SHADOW_READY,PAPER_READY",
        risk_usage=0,
        allocation_usage=1,
        normalization="SIGNED_LOG_CLAMPED",
        owner_stage="CAPITAL_GROWTH",
        version="V1",
    ),
    Metric(
        code="MAR_RATIO",
        name_ru="Коэффициент MAR",
        category="GROWTH",
        metric_level="DERIVED",
        formula="expected_cagr / max_drawdown",
        unit="ratio",
        direction="HIGHER_IS_BETTER",
        minimum_sample=60,
        calculation_window="MINIMUM_90_CALENDAR_DAYS",
        valid_min="-inf",
        valid_max="+inf",
        null_policy="INVALID_IF_MAX_DRAWDOWN_ZERO_OR_MISSING",
        source_relation="DERIVED",
        source_fields="EXPECTED_CAGR,MAX_DRAWDOWN",
        update_frequency="DAILY",
        lifecycle_usage="OOS_READY,SHADOW_READY,PAPER_READY",
        risk_usage=1,
        allocation_usage=1,
        normalization="SIGNED_LOG_CLAMPED",
        owner_stage="CAPITAL_GROWTH",
        version="V1",
    ),
    Metric(
        code="ULCER_INDEX",
        name_ru="Индекс язвительности просадки",
        category="RISK",
        metric_level="PRIMARY",
        formula=(
            "sqrt(mean(drawdown_fraction ** 2))"
        ),
        unit="fraction",
        direction="LOWER_IS_BETTER",
        minimum_sample=30,
        calculation_window="FULL_VALIDATION_WINDOW",
        valid_min="0",
        valid_max="1",
        null_policy="INVALID_IF_EQUITY_CURVE_MISSING",
        source_relation="analytics.edge_equity_curve_v1",
        source_fields="equity,observed_at",
        update_frequency="ON_EQUITY_UPDATE",
        lifecycle_usage="ROBUST,OOS_READY,SHADOW_READY,PAPER_READY",
        risk_usage=1,
        allocation_usage=1,
        normalization="INVERSE_CLAMPED_0_1",
        owner_stage="RISK",
        version="V1",
    ),
    Metric(
        code="RISK_OF_RUIN",
        name_ru="Вероятность разорения",
        category="RISK",
        metric_level="DERIVED",
        formula=(
            "monte_carlo_paths_with_equity_below_ruin_threshold "
            "/ monte_carlo_path_count"
        ),
        unit="fraction",
        direction="LOWER_IS_BETTER",
        minimum_sample=60,
        calculation_window="MINIMUM_10000_MONTE_CARLO_PATHS",
        valid_min="0",
        valid_max="1",
        null_policy="INVALID_IF_MONTE_CARLO_NOT_AVAILABLE",
        source_relation="analytics.edge_monte_carlo_v1",
        source_fields="ruined,path_count,ruin_threshold",
        update_frequency="ON_VALIDATION_RUN",
        lifecycle_usage="ROBUST,OOS_READY,SHADOW_READY,PAPER_READY",
        risk_usage=1,
        allocation_usage=1,
        normalization="INVERSE_CLAMPED_0_1",
        owner_stage="RISK",
        version="V1",
    ),
    Metric(
        code="KELLY_FRACTION",
        name_ru="Доля Келли",
        category="GROWTH",
        metric_level="DERIVED",
        formula=(
            "win_probability - "
            "((1 - win_probability) / payoff_ratio)"
        ),
        unit="fraction",
        direction="HIGHER_IS_BETTER_WITH_CAP",
        minimum_sample=60,
        calculation_window="ROLLING_200_TRADES",
        valid_min="-1",
        valid_max="1",
        null_policy="INVALID_IF_PAYOFF_RATIO_NON_POSITIVE",
        source_relation="DERIVED",
        source_fields="win_probability,payoff_ratio",
        update_frequency="ON_METRIC_REFRESH",
        lifecycle_usage="OOS_READY,SHADOW_READY,PAPER_READY",
        risk_usage=1,
        allocation_usage=1,
        normalization="CLAMPED_MINUS_1_TO_0_25",
        owner_stage="RISK",
        version="V1",
    ),
    Metric(
        code="CAPITAL_EFFICIENCY",
        name_ru="Эффективность капитала",
        category="GROWTH",
        metric_level="DERIVED",
        formula=(
            "annualized_net_profit "
            "/ average_capital_employed"
        ),
        unit="fraction_per_year",
        direction="HIGHER_IS_BETTER",
        minimum_sample=60,
        calculation_window="MINIMUM_90_CALENDAR_DAYS",
        valid_min="-inf",
        valid_max="+inf",
        null_policy="INVALID_IF_CAPITAL_EMPLOYED_NON_POSITIVE",
        source_relation="analytics.edge_capital_usage_v1",
        source_fields=(
            "net_profit,capital_employed,observed_at"
        ),
        update_frequency="DAILY",
        lifecycle_usage="OOS_READY,SHADOW_READY,PAPER_READY",
        risk_usage=0,
        allocation_usage=1,
        normalization="SIGNED_LOG_CLAMPED",
        owner_stage="CAPITAL_GROWTH",
        version="V1",
    ),
    Metric(
        code="ROBUSTNESS_SCORE",
        name_ru="Оценка устойчивости",
        category="ROBUSTNESS",
        metric_level="DERIVED",
        formula=(
            "weighted_mean("
            "walk_forward_score,oos_score,bootstrap_score,"
            "parameter_stability,regime_stability)"
        ),
        unit="score_0_100",
        direction="HIGHER_IS_BETTER",
        minimum_sample=60,
        calculation_window="LATEST_VALIDATION_VERSION",
        valid_min="0",
        valid_max="100",
        null_policy="INVALID_IF_ANY_REQUIRED_COMPONENT_MISSING",
        source_relation="analytics.edge_validation_summary_v1",
        source_fields=(
            "walk_forward_score,oos_score,bootstrap_score,"
            "parameter_stability,regime_stability"
        ),
        update_frequency="ON_VALIDATION_RUN",
        lifecycle_usage="ROBUST,OOS_READY,SHADOW_READY,PAPER_READY",
        risk_usage=1,
        allocation_usage=1,
        normalization="DIVIDE_BY_100",
        owner_stage="EDGE_GOVERNANCE",
        version="V1",
    ),
    Metric(
        code="LIQUIDITY_SCORE",
        name_ru="Оценка ликвидности",
        category="MARKET",
        metric_level="DERIVED",
        formula=(
            "weighted_mean(spread_score,volume_score,depth_score)"
        ),
        unit="score_0_100",
        direction="HIGHER_IS_BETTER",
        minimum_sample=100,
        calculation_window="ROLLING_20_SESSIONS",
        valid_min="0",
        valid_max="100",
        null_policy="INVALID_IF_MARKET_DATA_INCOMPLETE",
        source_relation="analytics.market_liquidity_snapshot_v1",
        source_fields=(
            "spread_score,volume_score,depth_score"
        ),
        update_frequency="DAILY",
        lifecycle_usage="OOS_READY,SHADOW_READY,PAPER_READY",
        risk_usage=1,
        allocation_usage=1,
        normalization="DIVIDE_BY_100",
        owner_stage="MARKET_DATA",
        version="V1",
    ),
    Metric(
        code="EXECUTION_QUALITY_SCORE",
        name_ru="Качество исполнения",
        category="EXECUTION",
        metric_level="DERIVED",
        formula=(
            "weighted_mean(fill_ratio_score,"
            "slippage_score,latency_score)"
        ),
        unit="score_0_100",
        direction="HIGHER_IS_BETTER",
        minimum_sample=30,
        calculation_window="ROLLING_100_ORDERS",
        valid_min="0",
        valid_max="100",
        null_policy="INVALID_IF_ORDER_SAMPLE_BELOW_MINIMUM",
        source_relation="analytics.execution_quality_v1",
        source_fields=(
            "fill_ratio_score,slippage_score,latency_score"
        ),
        update_frequency="ON_FILL",
        lifecycle_usage="SHADOW_READY,PAPER_READY",
        risk_usage=1,
        allocation_usage=1,
        normalization="DIVIDE_BY_100",
        owner_stage="EXECUTION",
        version="V1",
    ),
    Metric(
        code="CAPACITY_SCORE",
        name_ru="Оценка ёмкости edge",
        category="MARKET",
        metric_level="DERIVED",
        formula=(
            "min(1, executable_notional_without_material_slippage "
            "/ target_notional)"
        ),
        unit="score_0_100",
        direction="HIGHER_IS_BETTER",
        minimum_sample=20,
        calculation_window="ROLLING_20_SESSIONS",
        valid_min="0",
        valid_max="100",
        null_policy="INVALID_IF_TARGET_NOTIONAL_NON_POSITIVE",
        source_relation="analytics.edge_capacity_v1",
        source_fields=(
            "executable_notional_without_material_slippage,"
            "target_notional"
        ),
        update_frequency="DAILY",
        lifecycle_usage="SHADOW_READY,PAPER_READY",
        risk_usage=1,
        allocation_usage=1,
        normalization="IDENTITY_0_100",
        owner_stage="PORTFOLIO",
        version="V1",
    ),
    Metric(
        code="CORRELATION_PENALTY",
        name_ru="Штраф за корреляцию",
        category="PORTFOLIO",
        metric_level="DERIVED",
        formula=(
            "weighted_average_absolute_correlation_with_active_edges"
        ),
        unit="fraction",
        direction="LOWER_IS_BETTER",
        minimum_sample=60,
        calculation_window="ROLLING_90_CALENDAR_DAYS",
        valid_min="0",
        valid_max="1",
        null_policy="ZERO_ONLY_IF_NO_ACTIVE_EDGES",
        source_relation="analytics.edge_return_correlation_v1",
        source_fields=(
            "edge_candidate_id,peer_edge_candidate_id,"
            "correlation,capital_weight"
        ),
        update_frequency="DAILY",
        lifecycle_usage="SHADOW_READY,PAPER_READY,CAPITAL_ALLOCATED",
        risk_usage=1,
        allocation_usage=1,
        normalization="IDENTITY_0_1",
        owner_stage="PORTFOLIO",
        version="V1",
    ),
    Metric(
        code="CAPITAL_GROWTH_SCORE",
        name_ru="Итоговая оценка роста капитала",
        category="GROWTH",
        metric_level="COMPOSITE",
        formula=(
            "FORMULA_REGISTRY_REFERENCE_REQUIRED"
        ),
        unit="score_0_100",
        direction="HIGHER_IS_BETTER",
        minimum_sample=60,
        calculation_window="LATEST_COMPLETE_METRIC_SET",
        valid_min="0",
        valid_max="100",
        null_policy="INVALID_IF_ANY_REQUIRED_COMPONENT_MISSING",
        source_relation="DERIVED",
        source_fields=(
            "NET_EXPECTANCY,MAX_DRAWDOWN,EXPECTED_CAGR,"
            "MAR_RATIO,RISK_OF_RUIN,KELLY_FRACTION,"
            "CAPITAL_EFFICIENCY,ROBUSTNESS_SCORE,"
            "LIQUIDITY_SCORE,EXECUTION_QUALITY_SCORE,"
            "CAPACITY_SCORE,CORRELATION_PENALTY"
        ),
        update_frequency="ON_REQUIRED_METRIC_REFRESH",
        lifecycle_usage="SHADOW_READY,PAPER_READY,CAPITAL_ALLOCATED",
        risk_usage=1,
        allocation_usage=1,
        normalization="FORMULA_REGISTRY_REFERENCE_REQUIRED",
        owner_stage="CAPITAL_GROWTH",
        version="V1",
    ),
)

DEPENDENCIES = (
    Dependency(
        metric_code="RECOVERY_FACTOR",
        depends_on_metric_code="NET_EXPECTANCY",
        dependency_type="INPUT",
        required=1,
    ),
    Dependency(
        metric_code="RECOVERY_FACTOR",
        depends_on_metric_code="MAX_DRAWDOWN",
        dependency_type="INPUT",
        required=1,
    ),
    Dependency(
        metric_code="MAR_RATIO",
        depends_on_metric_code="EXPECTED_CAGR",
        dependency_type="INPUT",
        required=1,
    ),
    Dependency(
        metric_code="MAR_RATIO",
        depends_on_metric_code="MAX_DRAWDOWN",
        dependency_type="INPUT",
        required=1,
    ),
    Dependency(
        metric_code="CAPITAL_GROWTH_SCORE",
        depends_on_metric_code="NET_EXPECTANCY",
        dependency_type="REQUIRED_COMPONENT",
        required=1,
    ),
    Dependency(
        metric_code="CAPITAL_GROWTH_SCORE",
        depends_on_metric_code="MAX_DRAWDOWN",
        dependency_type="REQUIRED_COMPONENT",
        required=1,
    ),
    Dependency(
        metric_code="CAPITAL_GROWTH_SCORE",
        depends_on_metric_code="EXPECTED_CAGR",
        dependency_type="REQUIRED_COMPONENT",
        required=1,
    ),
    Dependency(
        metric_code="CAPITAL_GROWTH_SCORE",
        depends_on_metric_code="MAR_RATIO",
        dependency_type="REQUIRED_COMPONENT",
        required=1,
    ),
    Dependency(
        metric_code="CAPITAL_GROWTH_SCORE",
        depends_on_metric_code="RISK_OF_RUIN",
        dependency_type="REQUIRED_COMPONENT",
        required=1,
    ),
    Dependency(
        metric_code="CAPITAL_GROWTH_SCORE",
        depends_on_metric_code="KELLY_FRACTION",
        dependency_type="REQUIRED_COMPONENT",
        required=1,
    ),
    Dependency(
        metric_code="CAPITAL_GROWTH_SCORE",
        depends_on_metric_code="CAPITAL_EFFICIENCY",
        dependency_type="REQUIRED_COMPONENT",
        required=1,
    ),
    Dependency(
        metric_code="CAPITAL_GROWTH_SCORE",
        depends_on_metric_code="ROBUSTNESS_SCORE",
        dependency_type="REQUIRED_COMPONENT",
        required=1,
    ),
    Dependency(
        metric_code="CAPITAL_GROWTH_SCORE",
        depends_on_metric_code="LIQUIDITY_SCORE",
        dependency_type="REQUIRED_COMPONENT",
        required=1,
    ),
    Dependency(
        metric_code="CAPITAL_GROWTH_SCORE",
        depends_on_metric_code="EXECUTION_QUALITY_SCORE",
        dependency_type="REQUIRED_COMPONENT",
        required=1,
    ),
    Dependency(
        metric_code="CAPITAL_GROWTH_SCORE",
        depends_on_metric_code="CAPACITY_SCORE",
        dependency_type="REQUIRED_COMPONENT",
        required=1,
    ),
    Dependency(
        metric_code="CAPITAL_GROWTH_SCORE",
        depends_on_metric_code="CORRELATION_PENALTY",
        dependency_type="REQUIRED_COMPONENT",
        required=1,
    ),
)

LIFECYCLE_USAGES = tuple(
    LifecycleUsage(
        metric_code=metric.code,
        lifecycle_status=status,
        usage=(
            "REQUIRED"
            if status in metric.lifecycle_usage.split(",")
            else "NOT_USED"
        ),
        required=int(
            status in metric.lifecycle_usage.split(",")
        ),
    )
    for metric in METRICS
    for status in (
        "RESEARCH",
        "ROBUST",
        "OOS_READY",
        "SHADOW_READY",
        "PAPER_READY",
        "CAPITAL_ALLOCATED",
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
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    unresolved: list[dict[str, object]] = []

    metric_codes = [
        metric.code
        for metric in METRICS
    ]

    metric_code_set = set(metric_codes)

    duplicate_metric_code_count = (
        len(metric_codes)
        - len(metric_code_set)
    )

    if duplicate_metric_code_count:
        unresolved.append(
            {
                "scope": "METRIC",
                "identity": "",
                "reason": (
                    "DUPLICATE_METRIC_CODE_COUNT:"
                    f"{duplicate_metric_code_count}"
                ),
            }
        )

    for metric in METRICS:
        if metric.metric_level not in {
            "PRIMARY",
            "DERIVED",
            "COMPOSITE",
        }:
            unresolved.append(
                {
                    "scope": "METRIC",
                    "identity": metric.code,
                    "reason": "INVALID_METRIC_LEVEL",
                }
            )

        if metric.direction not in {
            "HIGHER_IS_BETTER",
            "LOWER_IS_BETTER",
            "HIGHER_IS_BETTER_WITH_CAP",
        }:
            unresolved.append(
                {
                    "scope": "METRIC",
                    "identity": metric.code,
                    "reason": "INVALID_DIRECTION",
                }
            )

        if metric.minimum_sample < 0:
            unresolved.append(
                {
                    "scope": "METRIC",
                    "identity": metric.code,
                    "reason": "NEGATIVE_MINIMUM_SAMPLE",
                }
            )

        if not metric.source_relation:
            unresolved.append(
                {
                    "scope": "METRIC",
                    "identity": metric.code,
                    "reason": "SOURCE_RELATION_MISSING",
                }
            )

        if not metric.formula:
            unresolved.append(
                {
                    "scope": "METRIC",
                    "identity": metric.code,
                    "reason": "FORMULA_MISSING",
                }
            )

    for dependency in DEPENDENCIES:
        if dependency.metric_code not in metric_code_set:
            unresolved.append(
                {
                    "scope": "DEPENDENCY",
                    "identity": dependency.metric_code,
                    "reason": "TARGET_METRIC_MISSING",
                }
            )

        if (
            dependency.depends_on_metric_code
            not in metric_code_set
        ):
            unresolved.append(
                {
                    "scope": "DEPENDENCY",
                    "identity": (
                        dependency.depends_on_metric_code
                    ),
                    "reason": "SOURCE_METRIC_MISSING",
                }
            )

        if (
            dependency.metric_code
            == dependency.depends_on_metric_code
        ):
            unresolved.append(
                {
                    "scope": "DEPENDENCY",
                    "identity": dependency.metric_code,
                    "reason": "SELF_DEPENDENCY",
                }
            )

    required_codes = {
        "NET_EXPECTANCY",
        "PROFIT_FACTOR",
        "MAX_DRAWDOWN",
        "RECOVERY_FACTOR",
        "EXPECTED_CAGR",
        "MAR_RATIO",
        "ULCER_INDEX",
        "RISK_OF_RUIN",
        "KELLY_FRACTION",
        "CAPITAL_EFFICIENCY",
        "ROBUSTNESS_SCORE",
        "LIQUIDITY_SCORE",
        "EXECUTION_QUALITY_SCORE",
        "CAPACITY_SCORE",
        "CORRELATION_PENALTY",
        "CAPITAL_GROWTH_SCORE",
    }

    missing_required_codes = sorted(
        required_codes - metric_code_set
    )

    for code in missing_required_codes:
        unresolved.append(
            {
                "scope": "REQUIRED_METRIC",
                "identity": code,
                "reason": "REQUIRED_METRIC_MISSING",
            }
        )

    write_tsv(
        METRICS_FILE,
        (
            "metric_code",
            "metric_name_ru",
            "category",
            "metric_level",
            "formula",
            "unit",
            "direction",
            "minimum_sample",
            "calculation_window",
            "valid_min",
            "valid_max",
            "null_policy",
            "source_relation",
            "source_fields",
            "update_frequency",
            "lifecycle_usage",
            "risk_usage",
            "allocation_usage",
            "normalization",
            "owner_stage",
            "version",
        ),
        [
            {
                "metric_code": metric.code,
                "metric_name_ru": metric.name_ru,
                "category": metric.category,
                "metric_level": metric.metric_level,
                "formula": metric.formula,
                "unit": metric.unit,
                "direction": metric.direction,
                "minimum_sample": metric.minimum_sample,
                "calculation_window": metric.calculation_window,
                "valid_min": metric.valid_min,
                "valid_max": metric.valid_max,
                "null_policy": metric.null_policy,
                "source_relation": metric.source_relation,
                "source_fields": metric.source_fields,
                "update_frequency": metric.update_frequency,
                "lifecycle_usage": metric.lifecycle_usage,
                "risk_usage": metric.risk_usage,
                "allocation_usage": metric.allocation_usage,
                "normalization": metric.normalization,
                "owner_stage": metric.owner_stage,
                "version": metric.version,
            }
            for metric in METRICS
        ],
    )

    write_tsv(
        DEPENDENCIES_FILE,
        (
            "metric_code",
            "depends_on_metric_code",
            "dependency_type",
            "required",
        ),
        [
            {
                "metric_code": item.metric_code,
                "depends_on_metric_code": (
                    item.depends_on_metric_code
                ),
                "dependency_type": item.dependency_type,
                "required": item.required,
            }
            for item in DEPENDENCIES
        ],
    )

    write_tsv(
        LIFECYCLE_FILE,
        (
            "metric_code",
            "lifecycle_status",
            "usage",
            "required",
        ),
        [
            {
                "metric_code": item.metric_code,
                "lifecycle_status": item.lifecycle_status,
                "usage": item.usage,
                "required": item.required,
            }
            for item in LIFECYCLE_USAGES
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

    category_count = len(
        {
            metric.category
            for metric in METRICS
        }
    )

    primary_count = sum(
        metric.metric_level == "PRIMARY"
        for metric in METRICS
    )

    derived_count = sum(
        metric.metric_level == "DERIVED"
        for metric in METRICS
    )

    composite_count = sum(
        metric.metric_level == "COMPOSITE"
        for metric in METRICS
    )

    with CONTRACT_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "CAPITAL GROWTH METRICS REGISTRY V1\n"
        )
        stream.write(
            "==================================\n\n"
        )
        stream.write(
            "PRIMARY_GOAL="
            "MAXIMIZE_LONG_TERM_CAPITAL_GROWTH\n"
        )
        stream.write("DATABASE=POSTGRESQL_ONLY\n")
        stream.write("METRIC_INLINE_CREATION_ALLOWED=0\n")
        stream.write(
            f"METRIC_COUNT={len(METRICS)}\n"
        )
        stream.write(
            f"CATEGORY_COUNT={category_count}\n"
        )
        stream.write(
            f"PRIMARY_METRIC_COUNT={primary_count}\n"
        )
        stream.write(
            f"DERIVED_METRIC_COUNT={derived_count}\n"
        )
        stream.write(
            f"COMPOSITE_METRIC_COUNT={composite_count}\n"
        )
        stream.write(
            f"DEPENDENCY_COUNT={len(DEPENDENCIES)}\n"
        )
        stream.write(
            "DUPLICATE_METRIC_CODE_COUNT="
            f"{duplicate_metric_code_count}\n"
        )
        stream.write(
            f"REQUIRED_METRIC_MISSING_COUNT="
            f"{len(missing_required_codes)}\n"
        )
        stream.write(
            f"UNRESOLVED_COUNT={len(unresolved)}\n"
        )
        stream.write(
            "CAPITAL_GROWTH_SCORE_FORMULA_STATUS="
            "DEFERRED_TO_FORMULA_REGISTRY_V1\n"
        )
        stream.write("RUNTIME_CHANGED=0\n")
        stream.write("EXECUTION_CHANGED=0\n")
        stream.write("ORDERS_CHANGED=0\n")
        stream.write("FILLS_CHANGED=0\n")
        stream.write("MICRO_LIVE_ALLOWED=0\n")

    print(
        "=== BUILD CAPITAL GROWTH "
        "METRICS REGISTRY V1 ==="
    )
    print(f"metric_count={len(METRICS)}")
    print(f"category_count={category_count}")
    print(f"primary_metric_count={primary_count}")
    print(f"derived_metric_count={derived_count}")
    print(f"composite_metric_count={composite_count}")
    print(
        f"dependency_count={len(DEPENDENCIES)}"
    )
    print(
        "duplicate_metric_code_count="
        f"{duplicate_metric_code_count}"
    )
    print(
        "required_metric_missing_count="
        f"{len(missing_required_codes)}"
    )
    print(f"unresolved_count={len(unresolved)}")

    for metric in METRICS:
        print(
            "METRIC "
            f"code={metric.code} "
            f"category={metric.category} "
            f"level={metric.metric_level} "
            f"direction={metric.direction} "
            f"minimum_sample={metric.minimum_sample} "
            f"owner={metric.owner_stage}"
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
        "CAPITAL_GROWTH_METRICS_REGISTRY_V1_READY"
    )

    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
