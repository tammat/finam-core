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
from finam_core.execution.managed_position_service import ManagedPositionService
from finam_core.execution.trade_management_service import TradeManagementService
from finam_core.execution.fill_event_router import FillEventRouter
from finam_core.portfolio.real_position_to_managed_sync import RealPositionToManagedSync


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

    try:
        await feed.start(Settings.SYMBOL)
        print("LIVE_FEED_STARTED", flush=True)
    except Exception as e:
        print(f"LIVE_FEED_START_FAILED error={e}", flush=True)



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
    # Managed positions
    # -----------------------------
    managed_positions = ManagedPositionService()
    restored_positions = managed_positions.restore_from_repository()
    print(f"MANAGED_POSITIONS_RESTORED count={restored_positions}", flush=True)
    synced_positions = RealPositionToManagedSync(managed=managed_positions).sync()
    print(f"REAL_POSITIONS_SYNCED_TO_MANAGED count={synced_positions}", flush=True)

    # -----------------------------
    # Trade management
    # -----------------------------
    trade_management = TradeManagementService()
    fill_event_router = FillEventRouter(trade_management)

    # -----------------------------
    # Trade management
    # -----------------------------
    trade_management = TradeManagementService()
    fill_event_router = FillEventRouter(trade_management)

    # -----------------------------
    # Trading pipeline
    # -----------------------------
    pipeline = TradingPipeline(
        portfolio=portfolio,
        risk_engine=risk_engine,
        execution=execution
    )
    pipeline.fill_event_router = fill_event_router

    pipeline.managed_positions = managed_positions

    print("BOOTSTRAP_COMPLETE", flush=True)

    return pipeline, event_bus, gateway, feed