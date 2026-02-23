import os

from execution.trading_engine import TradingEngine
from accounting.portfolio_manager import PortfolioManager
from execution.order_manager import OrderManager
from risk.pre_trade_risk import PreTradeRiskEngine, RiskConfig
from storage.postgres_event_store import PostgresEventStore
from storage.postgres_snapshot_store import PostgresSnapshotStore


def build_engine(dsn: str):
    event_store = PostgresEventStore(dsn)
    snapshot_store = PostgresSnapshotStore(dsn)

    pm = PortfolioManager(initial_cash=100_000.0)
    risk_config = RiskConfig(
        max_risk_per_trade=0.02,
        max_total_exposure=1_000_000.0,
        daily_loss_limit=1_000_000.0,
    )
    risk = PreTradeRiskEngine(risk_config)
    oms = OrderManager()

    engine = TradingEngine(
        portfolio_manager=pm,
        risk_engine=risk,
        order_manager=oms,
        event_store=event_store,
        snapshot_store=snapshot_store,
    )

    return engine


def main():
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        raise RuntimeError("POSTGRES_DSN not set")

    stream = "portfolio-1"

    # --- очистка для детерминированности ---
    store = PostgresEventStore(dsn)
    with store._get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM events WHERE stream = %s", (stream,))
            cur.execute("DELETE FROM stream_snapshots WHERE stream = %s", (stream,))
        conn.commit()

    # --- первая инстанция ---
    engine1 = build_engine(dsn)

    # > snapshot_interval (по умолчанию 50)
    for _ in range(60):
        engine1.process_signal("NG", "BUY", 1, 1.0)

    state_after = engine1.live_pm.compute_state()

    # --- симуляция рестарта ---
    engine2 = build_engine(dsn)
    state_replayed = engine2.live_pm.compute_state()

    print("State after:", state_after)
    print("State replayed:", state_replayed)

    assert state_after.cash == state_replayed.cash
    assert state_after.equity == state_replayed.equity
    assert state_after.exposure == state_replayed.exposure

    print("ok: snapshot bootstrap works")


if __name__ == "__main__":
    raise SystemExit(main())