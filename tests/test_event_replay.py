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

    pm = PortfolioManager()

    store.replay_stream(
        stream="portfolio-1",
        handler=pm.handle_event
    )

    state = pm.compute_state()

    print("Replay state:", state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())