import os

from core.event_bus import EventBus
from core.engine import Engine

from data.market_data import DummyMarketData
from strategy.momentum import MomentumStrategy
from ai.ml_strategy import MLStrategy

from portfolio.portfolio import Portfolio
from risk.risk_engine import RiskEngine
from execution.sim_execution_engine import SimExecutionEngine
from storage.postgres import PostgresStorage


def build_execution_engine(mode: str, event_bus: EventBus, storage: PostgresStorage):
    """
    Returns execution engine instance based on MODE.
    SIM: SimExecutionEngine
    REAL: FinamExecutionEngine (through infra/finam/adapter.py + vendor finam_grpc_client)
    """
    if mode.upper() != "REAL":
        return SimExecutionEngine(event_bus=event_bus, price_resolver=storage.last_price)

    # REAL mode
    token = os.getenv("FINAM_TOKEN")
    account_id = os.getenv("FINAM_ACCOUNT_ID")
    if not token or not account_id:
        raise RuntimeError("REAL mode requires FINAM_TOKEN and FINAM_ACCOUNT_ID in env")

    # Lazy import: so SIM works even if REAL modules are not yet added
    from execution.finam_execution_engine import FinamExecutionEngine

    allow_trading = os.getenv("ALLOW_TRADING", "0") == "1"
    return FinamExecutionEngine(
        token=token,
        account_id=account_id,
        allow_trading=allow_trading,
    )


def main() -> int:
    mode = os.getenv("MODE", "SIM").upper()
    print(f"MODE={mode}")

    event_bus = EventBus()

    # Storage (PostgreSQL)
    dsn = os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5432/finam_core")
    storage = PostgresStorage(dsn)
    # Market data
    # NOTE: пока не сделали real-time marketdata ingestion для REAL,
    # используем DummyMarketData даже в REAL для проверки связности pipeline.
    data = DummyMarketData(event_bus)

    # Strategies
    strategies = [MomentumStrategy(event_bus)]
    if os.getenv("ENABLE_ML", "1") == "1":
        strategies.append(MLStrategy(event_bus))

    # Portfolio + Risk
    portfolio = Portfolio()
    risk = RiskEngine(
        portfolio=portfolio,
        event_bus=event_bus,
        price_resolver=storage.last_price,
    )

    # Execution
    execution = build_execution_engine(mode, event_bus, storage)

    engine = Engine(
        data=data,
        strategies=strategies,
        risk=risk,
        execution=execution,
        portfolio=portfolio,
        storage=storage,
    )

    try:
        storage.apply_migrations()
        processed = engine.run()
    finally:
        # graceful shutdown for REAL execution
        close = getattr(execution, "close", None)
        if callable(close):
            close()

    print("Processed events:", processed)
    print("Positions:", getattr(portfolio, "positions", None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())