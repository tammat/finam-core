import os
import asyncio

from finam_core.events.event_bus import EventBus
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
    gateway = FinamGateway(event_bus=event_bus)

    # -----------------------------
    # Market data feed
    # -----------------------------
    feed = LiveMarketFeed(
        gateway.marketdata,
        event_bus
    )

    if hasattr(gateway.marketdata, "subscribe_bars"):
        await feed.start(Settings.SYMBOL)
    else:
        print("LIVE_FEED_DISABLED: marketdata has no subscribe_bars; using EventBus market stream")


    # -----------------------------
    # Portfolio
    # -----------------------------
    portfolio = PortfolioManager(initial_cash=float(getattr(Settings, 'INITIAL_CASH', 1000000)))

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
    if str(getattr(Settings, "EXECUTION_ENABLED", "0")) == "1":
        execution = FinamExecutionEngine(
            token=getattr(gateway.token_manager, "token", None) or getattr(Settings, "FINAM_TOKEN", ""),
            account_id=getattr(Settings, "FINAM_ACCOUNT_ID", ""),
        )
    else:
        execution = None
        print("EXECUTION_DISABLED: real execution engine not initialized")


    # -----------------------------
    # Trading pipeline
    # -----------------------------
    pipeline = TradingPipeline(
        portfolio=portfolio,
        risk_engine=risk_engine,
        execution=execution
    )

    return pipeline, event_bus, gateway, feed