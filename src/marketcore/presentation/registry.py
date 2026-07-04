from __future__ import annotations

from marketcore.presentation.pages.strategy_workbench import StrategyWorkbenchPage
from marketcore.presentation.pages.feature_store import FeatureStorePage
from marketcore.presentation.pages.edge_pipeline_v2_legacy_aliases import EdgePipelineV2MicroLiveAliasPage, EdgePipelineV2OosBacktestAliasPage, EdgePipelineV2OosValidationAliasPage, EdgePipelineV2PaperEdgeDiscoveryAliasPage, EdgePipelineV2RobustnessAliasPage, EdgePipelineV2ValidationPipelineAliasPage, EdgePipelineV2ValidationQueueAliasPage
from marketcore.presentation.pages.edge_pipeline_v2 import EdgePipelineV2Page
from marketcore.presentation.page import Page
from marketcore.presentation.pages.ai import AiPage
from marketcore.presentation.pages.home import HomePage
from marketcore.presentation.pages.market_universe_research_queue import MarketUniverseResearchQueuePage
from marketcore.presentation.pages.market_universe_ranking import MarketUniverseRankingPage
from marketcore.presentation.pages.paper_edge_market_symbol_alias_plan import PaperEdgeMarketSymbolAliasPlanPage
from marketcore.presentation.pages.paper_edge_market_data_freshness import PaperEdgeMarketDataFreshnessPage
from marketcore.presentation.pages.paper_edge_market_data_binding import PaperEdgeMarketDataBindingPage
from marketcore.presentation.pages.marketcore_ui_route_health_matrix import MarketcoreUiRouteHealthMatrixPage
from marketcore.presentation.pages.marketcore_ui_systemd_health import MarketcoreUiSystemdHealthPage
from marketcore.presentation.pages.paper_runtime_sample_collection_daily_summary import PaperRuntimeSampleCollectionDailySummaryPage
from marketcore.presentation.pages.settings import SettingsPage
from marketcore.presentation.pages.paper_sample_operations_timer_health import PaperSampleOperationsTimerHealthPage
from marketcore.presentation.pages.paper_runtime_sample_collection_operations import PaperRuntimeSampleCollectionOperationsPage
from marketcore.presentation.pages.phase_ii_paper_edge_discovery_summary import PhaseIiPaperEdgeDiscoverySummaryPage
from marketcore.presentation.pages.paper_runtime_sample_collection_phase_close import PaperRuntimeSampleCollectionPhaseClosePage
from marketcore.presentation.pages.paper_sample_collection_timer_health import PaperSampleCollectionTimerHealthPage
from marketcore.presentation.pages.paper_sample_accumulation_monitor import PaperSampleAccumulationMonitorPage
from marketcore.presentation.pages.micro_live_readiness import MicroLiveReadinessPage
from marketcore.presentation.pages.edge_oos_backtest import EdgeOosBacktestPage
from marketcore.presentation.pages.edge_oos_validation import EdgeOosValidationPage
from marketcore.presentation.pages.edge_robustness_check import EdgeRobustnessCheckPage
from marketcore.presentation.pages.edge_validation_pipeline import EdgeValidationPipelinePage
from marketcore.presentation.pages.edge_validation_queue import EdgeValidationQueuePage
from marketcore.presentation.pages.paper_edge_discovery import PaperEdgeDiscoveryPage
from marketcore.presentation.pages.knowledge_graph import KnowledgeGraphPage
from marketcore.presentation.pages.logs import LogsPage
from marketcore.presentation.pages.orders import OrdersPage
from marketcore.presentation.pages.portfolio import PortfolioPage
from marketcore.presentation.pages.research import ResearchPage
from marketcore.presentation.pages.risk import RiskPage
from marketcore.presentation.pages.runtime import RuntimePage
from marketcore.presentation.pages.system import SystemPage
from marketcore.presentation.pages.validation import ValidationPage


PAGES: list[Page] = [
    HomePage(),
    SettingsPage(),
    MarketcoreUiSystemdHealthPage(),
    MarketcoreUiRouteHealthMatrixPage(),
    EdgePipelineV2PaperEdgeDiscoveryAliasPage(),
    PaperEdgeMarketDataBindingPage(),
    PaperEdgeMarketDataFreshnessPage(),
    PaperEdgeMarketSymbolAliasPlanPage(),
    MarketUniverseRankingPage(),
    MarketUniverseResearchQueuePage(),
    EdgePipelineV2ValidationQueueAliasPage(),
    EdgePipelineV2ValidationPipelineAliasPage(),
    EdgePipelineV2RobustnessAliasPage(),
    EdgePipelineV2OosValidationAliasPage(),
    EdgePipelineV2OosBacktestAliasPage(),
    EdgePipelineV2MicroLiveAliasPage(),
    PaperSampleAccumulationMonitorPage(),
    PaperSampleCollectionTimerHealthPage(),
    PaperRuntimeSampleCollectionPhaseClosePage(),
    PhaseIiPaperEdgeDiscoverySummaryPage(),
    PaperRuntimeSampleCollectionOperationsPage(),
    PaperSampleOperationsTimerHealthPage(),
    PaperRuntimeSampleCollectionDailySummaryPage(),
    RuntimePage(),
    KnowledgeGraphPage(),
    ResearchPage(),
    PortfolioPage(),
    OrdersPage(),
    RiskPage(),
    ValidationPage(),
    LogsPage(),
    SystemPage(),
    AiPage(),
    EdgePipelineV2Page(),
    FeatureStorePage(),
    StrategyWorkbenchPage(),
]


def get_page(path: str) -> Page | None:
    for page in PAGES:
        if page.route == path:
            return page
    return None


def menu_pages() -> list[Page]:
    return sorted(PAGES, key=lambda p: p.menu_order)
