import os
from dotenv import load_dotenv

from storage.postgres_event_store import PostgresEventStore
from execution.trading_engine import TradingEngine
from accounting.portfolio_manager import PortfolioManager
from risk.pre_trade_risk import PreTradeRiskEngine, RiskConfig


STREAM = "portfolio-1"


def build_engine(dsn):
    event_store = PostgresEventStore(dsn)

    risk = PreTradeRiskEngine(
        RiskConfig(
            max_risk_per_trade=1.0,
            daily_loss_limit=1_000_000,
            max_total_exposure=1_000_000,
        )
    )

    engine = TradingEngine(
        dsn=dsn,
        portfolio_manager_cls=PortfolioManager,
        risk_engine=risk,
        event_store=event_store,
    )

    return engine


def main():
    load_dotenv()
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        raise RuntimeError("POSTGRES_DSN not set")

    # 1️⃣ First engine instance
    engine1 = build_engine(dsn)

    # Generate executions
    engine1.process_signal("NG", "BUY", 1, 100)
    engine1.process_signal("NG", "BUY", 1, 110)

    live_state_before = engine1.live_pm.compute_state()

    # 2️⃣ Simulate restart (destroy engine1)
    del engine1

    # 3️⃣ New engine instance (should bootstrap from DB)
    engine2 = build_engine(dsn)

    live_state_after = engine2.live_pm.compute_state()

    # 4️⃣ Strict equality checks
    assert live_state_before.cash == live_state_after.cash
    assert live_state_before.equity == live_state_after.equity
    assert live_state_before.exposure == live_state_after.exposure
    assert live_state_before.realized_pnl == live_state_after.realized_pnl
    assert live_state_before.unrealized_pnl == live_state_after.unrealized_pnl

    print("ok: engine restart simulation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())