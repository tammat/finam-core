import os
from dotenv import load_dotenv

from storage.postgres_event_store import PostgresEventStore
from accounting.portfolio_manager import PortfolioManager


def main():
    load_dotenv()
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        raise RuntimeError("POSTGRES_DSN not set")

    store = PostgresEventStore(dsn)

    # 1) append execution event
    store.append(
        stream="portfolio-1",
        event_type="ExecutionEvent",
        payload={
            "fill_id": "test_fill_1",
            "symbol": "NG",
            "side": "BUY",
            "qty": 1.0,
            "price": 100.0,
            "commission": 1.0,
        },
        version=1,
    )

    # 2) replay
    pm = PortfolioManager()
    store.replay_stream("portfolio-1", pm.handle_event)

    state = pm.compute_state()
    print("Replay state:", state)

    # 3) sanity checks
    if state.cash >= 100000.0:
        raise RuntimeError("EXPECTED_CASH_DECREASE_AFTER_BUY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())