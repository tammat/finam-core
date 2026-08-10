from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResearchMetricVM:
    title: str
    value: str
    status: str
    action_label: str = "Подробнее"
    action_href: str = "#"


@dataclass(frozen=True)
class ResearchCandidateVM:
    symbol: str
    strategy: str
    timeframe: str
    trades: str
    pnl: str
    pf: str
    status: str


@dataclass(frozen=True)
class ResearchCheckVM:
    check: str
    result: str
    status: str


@dataclass(frozen=True)
class ResearchEdgeValidationVM:
    symbol: str
    robustness: str
    positive_variants: str
    stable_variants: str
    cost_status: str
    net_pnl: str
    net_expectancy: str
    net_profit_factor: str
    economic_edge: str
    micro_live: str


@dataclass(frozen=True)
class ResearchCenterVM:
    title: str = "Исследования"
    subtitle: str = "Research Center"

    overview: list[ResearchMetricVM] = field(default_factory=list)
    candidates: list[ResearchCandidateVM] = field(default_factory=list)
    checks: list[ResearchCheckVM] = field(default_factory=list)
    edge_validation: list[ResearchEdgeValidationVM] = field(default_factory=list)
    actions: list[ResearchMetricVM] = field(default_factory=list)


def build_default_research_center_vm() -> ResearchCenterVM:
    return ResearchCenterVM(
        overview=[
            ResearchMetricVM("Кандидаты", "1", "READY", "Открыть", "/research"),
            ResearchMetricVM("Replay", "Готово", "READY", "Детали", "/research"),
            ResearchMetricVM("OOS", "План", "WARNING", "Детали", "/research"),
            ResearchMetricVM("Edge", "Есть", "READY", "Детали", "/research"),
        ],
        candidates=[
            ResearchCandidateVM(
                "BRM6@RTSX",
                "BR Breakout",
                "M5",
                "77",
                "147,29",
                "1,94",
                "READY",
            ),
        ],
        checks=[
            ResearchCheckVM("Forensic", "Готово", "READY"),
            ResearchCheckVM("Robustness", "План", "WARNING"),
            ResearchCheckVM("OOS", "План", "WARNING"),
        ],
        actions=[
            ResearchMetricVM("Кандидат", "BRM6", "READY", "Открыть", "/research"),
            ResearchMetricVM("Риски", "Проверить", "HIGH", "Открыть", "/risk"),
            ResearchMetricVM("Рынок", "BR", "READY", "Открыть", "/market"),
        ],
    )
