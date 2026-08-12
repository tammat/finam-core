from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Callable, Mapping
from threading import Lock
from time import monotonic

from marketcore.presentation.render_tree.v2 import (
    RenderDocumentV2,
    validate_render_document_v2,
)
from marketcore.presentation.services.operator_settings_v1 import OperatorSettingsV1
from marketcore.presentation.workspace_v2.presenter.control_center_v2_presenter import (
    ControlCenterV2Presenter,
)
from marketcore.presentation.workspace_v2.presenter.home_v2_presenter import HomeV2Presenter
from marketcore.presentation.workspace_v2.presenter.portfolio_v2_presenter import (
    PortfolioV2Presenter,
)
from marketcore.presentation.workspace_v2.renderer.control_center_v2_domain_renderer import (
    render_control_center_domain_v2,
)
from marketcore.presentation.workspace_v2.resolver.control_compact_v3_resolver import ControlCompactV3Resolver
from marketcore.services.research.research_center_service import (
    ResearchCenterService,
)
from marketcore.presentation.workspace_v2.renderer.control_compact_v3_domain_renderer import render_control_compact_v3
from marketcore.presentation.workspace_v2.renderer.home_v2_domain_renderer import (
    render_home_domain_v2,
)
from marketcore.presentation.workspace_v2.renderer.home_compact_v1_domain_renderer import (
    render_home_compact_v1,
)
from marketcore.presentation.workspace_v2.renderer.portfolio_v2_domain_renderer import (
    render_portfolio_domain_v2,
)
from marketcore.presentation.workspace_v2.renderer.settings_v2_domain_renderer import (
    render_settings_domain_v2,
)
from marketcore.presentation.workspace_v2.renderer.capital_v2_domain_renderer import render_capital_domain_v2
from marketcore.presentation.workspace_v2.resolver.portfolio_v2_resolver import PortfolioV2Resolver
from marketcore.presentation.workspace_v2.resolver.risk_v2_resolver import RiskV2Resolver
from marketcore.presentation.workspace_v2.renderer.risk_v2_domain_renderer import render_risk_domain_v2
from marketcore.presentation.workspace_v2.resolver.research_v2_resolver import ResearchV2Resolver
from marketcore.presentation.workspace_v2.renderer.research_v2_domain_renderer import render_research_domain_v2
from marketcore.presentation.workspace_v2.resolver.intraday_v2_resolver import IntradayV2Resolver
from marketcore.presentation.workspace_v2.renderer.intraday_v2_domain_renderer import render_intraday_domain_v2
from marketcore.presentation.workspace_v2.resolver.program_v2_resolver import ProgramV2Resolver
from marketcore.presentation.workspace_v2.renderer.program_v2_domain_renderer import render_program_domain_v2


class DomainProducerCodeV2(str, Enum):
    HOME = "HOME"
    PORTFOLIO = "PORTFOLIO"
    CONTROL_CENTER = "CONTROL_CENTER"
    SETTINGS = "SETTINGS"
    CAPITAL = "CAPITAL"
    RISK = "RISK"
    RESEARCH = "RESEARCH"
    INTRADAY = "INTRADAY"
    PROGRAM = "PROGRAM"


class DomainProducerRegistryErrorV2(ValueError):
    pass


_COMPACT_CACHE_LOCK = Lock()
_COMPACT_CACHE: tuple[float, dict] | None = None
_COMPACT_CACHE_TTL_SECONDS = 15.0


def _compact_snapshot() -> dict:
    global _COMPACT_CACHE
    now = monotonic()
    cached = _COMPACT_CACHE
    if cached is not None and now - cached[0] < _COMPACT_CACHE_TTL_SECONDS:
        return cached[1]
    with _COMPACT_CACHE_LOCK:
        cached = _COMPACT_CACHE
        if cached is not None and now - cached[0] < _COMPACT_CACHE_TTL_SECONDS:
            return cached[1]
        snapshot = ControlCompactV3Resolver().resolve()

        frontier = ResearchCenterService().load().frontier

        snapshot = dict(snapshot)
        snapshot["physical_edge_frontier"] = {
            "status": frontier.status,
            "target_candidates": frontier.target_candidates,
            "contract_mixing_allowed":
                frontier.contract_mixing_allowed,
            "source_read_only":
                frontier.source_read_only,
            "rows": tuple(
                {
                    "rank": row.rank,
                    "physical_symbol": row.physical_symbol,
                    "strategy": row.strategy,
                    "side": row.side,
                    "state": row.state,
                    "pairs": row.pairs,
                    "oos_pairs": row.oos_pairs,
                    "net_expectancy": row.net_expectancy,
                    "paired_gain": row.paired_gain,
                    "placebo_delta": row.placebo_delta,
                }
                for row in frontier.rows[:3]
            ),
        }

        _COMPACT_CACHE = (monotonic(), snapshot)
        return snapshot


@dataclass(frozen=True, slots=True)
class DomainProducerDefinitionV2:
    producer_code: DomainProducerCodeV2
    document_id: str
    owner_code: str
    build: Callable[[str], RenderDocumentV2]


def _build_home(timezone_code: str) -> RenderDocumentV2:
    return render_home_compact_v1(
        _compact_snapshot(), timezone_code=timezone_code
    )


def _build_portfolio(timezone_code: str) -> RenderDocumentV2:
    settings = OperatorSettingsV1.load(timezone=timezone_code)
    return render_portfolio_domain_v2(
        PortfolioV2Presenter(settings=settings).load(limit=200),
        timezone_code=settings.timezone,
    )


def _build_control_center(timezone_code: str) -> RenderDocumentV2:
    return render_control_compact_v3(
        _compact_snapshot(),
        timezone_code=timezone_code,
        document_id="operator.control_center.v2",
    )


def _build_settings(timezone_code: str) -> RenderDocumentV2:
    return render_settings_domain_v2(
        OperatorSettingsV1.load(timezone=timezone_code),
    )


def _build_capital(timezone_code: str) -> RenderDocumentV2:
    return render_capital_domain_v2(PortfolioV2Resolver().resolve(), timezone_code=timezone_code)


def _build_risk(timezone_code: str) -> RenderDocumentV2:
    return render_risk_domain_v2(RiskV2Resolver().resolve(), timezone_code=timezone_code)

def _build_research(timezone_code: str) -> RenderDocumentV2:
    return render_research_domain_v2(ResearchV2Resolver().resolve(), timezone_code=timezone_code)

def _build_intraday(timezone_code: str) -> RenderDocumentV2:
    return render_intraday_domain_v2(IntradayV2Resolver().resolve(timezone_code=timezone_code), timezone_code=timezone_code)

def _build_program(timezone_code: str) -> RenderDocumentV2:
    return render_program_domain_v2(ProgramV2Resolver().resolve(),timezone_code=timezone_code)


_DEFINITIONS: Mapping[DomainProducerCodeV2, DomainProducerDefinitionV2] = MappingProxyType(
    {
        DomainProducerCodeV2.HOME: DomainProducerDefinitionV2(
            producer_code=DomainProducerCodeV2.HOME,
            document_id="operator.home.v2",
            owner_code="OPERATOR_HOME",
            build=_build_home,
        ),
        DomainProducerCodeV2.PORTFOLIO: DomainProducerDefinitionV2(
            producer_code=DomainProducerCodeV2.PORTFOLIO,
            document_id="operator.portfolio.v2",
            owner_code="PORTFOLIO",
            build=_build_portfolio,
        ),
        DomainProducerCodeV2.CONTROL_CENTER: DomainProducerDefinitionV2(
            producer_code=DomainProducerCodeV2.CONTROL_CENTER,
            document_id="operator.control_center.v2",
            owner_code="EDGE_CONTROL",
            build=_build_control_center,
        ),
        DomainProducerCodeV2.SETTINGS: DomainProducerDefinitionV2(
            producer_code=DomainProducerCodeV2.SETTINGS,
            document_id="operator.settings.v2",
            owner_code="SETTINGS",
            build=_build_settings,
        ),
        DomainProducerCodeV2.CAPITAL: DomainProducerDefinitionV2(
            producer_code=DomainProducerCodeV2.CAPITAL,
            document_id="operator.capital.v2",
            owner_code="CAPITAL",
            build=_build_capital,
        ),
        DomainProducerCodeV2.RISK: DomainProducerDefinitionV2(
            producer_code=DomainProducerCodeV2.RISK,
            document_id="operator.risk.v2",
            owner_code="RISK",
            build=_build_risk,
        ),
        DomainProducerCodeV2.RESEARCH: DomainProducerDefinitionV2(
            producer_code=DomainProducerCodeV2.RESEARCH, document_id="operator.research.v2", owner_code="RESEARCH", build=_build_research,
        ),
        DomainProducerCodeV2.INTRADAY: DomainProducerDefinitionV2(producer_code=DomainProducerCodeV2.INTRADAY,document_id="operator.intraday.v2",owner_code="INTRADAY",build=_build_intraday),
        DomainProducerCodeV2.PROGRAM: DomainProducerDefinitionV2(producer_code=DomainProducerCodeV2.PROGRAM,document_id="operator.program.v2",owner_code="PROGRAM",build=_build_program),
    }
)


def domain_producer_definitions_v2() -> tuple[DomainProducerDefinitionV2, ...]:
    return tuple(_DEFINITIONS[code] for code in DomainProducerCodeV2)


def build_domain_document_v2(
    producer_code: DomainProducerCodeV2 | str,
    *,
    timezone_code: str | None = None,
) -> RenderDocumentV2:
    try:
        normalized_code = (
            producer_code
            if isinstance(producer_code, DomainProducerCodeV2)
            else DomainProducerCodeV2(str(producer_code).strip().upper())
        )
    except ValueError as exc:
        raise DomainProducerRegistryErrorV2(
            f"DOMAIN_PRODUCER_V2_UNKNOWN:{producer_code}"
        ) from exc

    definition = _DEFINITIONS[normalized_code]
    settings = OperatorSettingsV1.load(timezone=timezone_code)
    document = definition.build(settings.timezone)
    validate_render_document_v2(document)

    if document.document_id != definition.document_id:
        raise DomainProducerRegistryErrorV2(
            "DOMAIN_PRODUCER_V2_DOCUMENT_ID_MISMATCH:"
            f"{normalized_code.value}:{document.document_id}"
        )
    return document
