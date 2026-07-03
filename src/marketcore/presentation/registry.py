from __future__ import annotations

from marketcore.presentation.page import Page
from marketcore.presentation.pages.ai import AiPage
from marketcore.presentation.pages.home import HomePage
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
    PaperEdgeDiscoveryPage(),
    EdgeValidationQueuePage(),
    EdgeValidationPipelinePage(),
    EdgeRobustnessCheckPage(),
    EdgeOosValidationPage(),
    EdgeOosBacktestPage(),
    MicroLiveReadinessPage(),
    PaperSampleAccumulationMonitorPage(),
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
]


def get_page(path: str) -> Page | None:
    for page in PAGES:
        if page.route == path:
            return page
    return None


def menu_pages() -> list[Page]:
    return sorted(PAGES, key=lambda p: p.menu_order)
