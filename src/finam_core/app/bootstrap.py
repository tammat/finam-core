import os
import asyncio

from finam_core.core.event_bus import EventBus
from finam_core.gateway.finam_gateway import FinamGateway
from finam_core.ingestion.live_market_feed import LiveMarketFeed

from finam_core.core.orchestrator import TradingPipeline
from finam_core.risk.risk_engine import RiskEngine
from finam_core.risk.MaxPositionPctRule import MaxPositionPctRule
from finam_core.risk.MaxGrossExposureRule import MaxGrossExposureRule
from finam_core.risk.DrawdownRule import DrawdownRule

from finam_core.execution.finam_execution_engine import FinamExecutionEngine
from finam_core.accounting.portfolio_manager import PortfolioManager

from finam_core.config.settings import Settings


async def bootstrap():

    # -----------------------------
    # EventBus
    # -----------------------------
    event_bus = EventBus()

    # -----------------------------
    # Gateway
    # -----------------------------
    gateway = FinamGateway()

    # -----------------------------
    # Market data feed
    # -----------------------------
    feed = LiveMarketFeed(
        gateway.marketdata,
        event_bus
    )

    await feed.start(Settings.SYMBOL)

    # -----------------------------
    # Portfolio
    # -----------------------------
    portfolio = PortfolioManager()

    # -----------------------------
    # Risk engine
    # -----------------------------
    risk_engine = RiskEngine([
        MaxPositionPctRule(Settings.MAX_POSITION_PCT),
        MaxGrossExposureRule(Settings.MAX_GROSS_EXPOSURE_PCT),
        DrawdownRule(Settings.MAX_DRAWDOWN_PCT),
    ])

    # -----------------------------
    # Execution
    # -----------------------------
    execution = FinamExecutionEngine(gateway)

    # -----------------------------
    # Trading pipeline
    # -----------------------------
    pipeline = TradingPipeline(
        event_bus=event_bus,
        portfolio=portfolio,
        risk_engine=risk_engine,
        execution=execution
    )

    return pipeline, event_bus, gateway, feed